from typing import Union
import xml.etree.ElementTree as ET

class PomService:

    def __init__(self, pom_source: Union[str, bytes]):
        self.namespace = {'mvn': 'http://maven.apache.org/POM/4.0.0'}
        
        # Check if pom_source is a file path or XML content
        try:
            # Attempt to parse as XML content
            self.tree = ET.ElementTree(ET.fromstring(pom_source))
        except ET.ParseError:
            # If parsing fails, assume it's a file path
            self.pom_path = pom_source
            self.tree = ET.parse(pom_source)
        
        self.root = self.tree.getroot()
        self.properties = self.root.find('mvn:properties', self.namespace)

    def __normalize_java_version(self, version: str) -> str:
        if version.startswith("1."):
            return version
        try:
            version_num = int(version)
            if version_num < 10:
                return f"1.{version_num}"
            return str(version_num)
        except ValueError:
            return version
    
    def __resolve_property(self, value) -> str:
        if value and value.startswith('${') and value.endswith('}'):
            property_name = value[2:-1]
            property_value = self.properties.find(f'mvn:{property_name}', self.namespace) if self.properties is not None else None
            if property_value is not None:
                return str(property_value.text)
        return value
    
    def __get_java_version_from_properties(self) -> Union[str, None]:
        if self.properties is not None:
            java_version = self.properties.find('mvn:maven.compiler.source', self.namespace)
            if java_version is None:
                java_version = self.properties.find('mvn:java.version', self.namespace)
            
            if java_version is not None:
                return self.__resolve_property(java_version.text)
        return None
    
    def __get_java_version_from_plugins(self) -> Union[str, None]:
        build = self.root.find('mvn:build', self.namespace)
        if build is not None:
            # Check in plugins section
            java_version = self.__find_java_version_in_plugin_container(build.find('mvn:plugins', self.namespace))
            if java_version is not None:
                return java_version
            
            # Check in pluginManagement section
            plugin_management = build.find('mvn:pluginManagement', self.namespace)
            if plugin_management is not None:
                java_version = self.__find_java_version_in_plugin_container(plugin_management.find('mvn:plugins', self.namespace))
                if java_version is not None:
                    return java_version
        
        return None
    
    def __get_java_version_from_profiles(self) -> Union[str, None]:
        profiles = self.root.find('mvn:profiles', self.namespace)
        if profiles is not None:
            for profile in profiles.findall('mvn:profile', self.namespace):
                build = profile.find('mvn:build', self.namespace)
                if build is not None:
                    java_version = self.__find_java_version_in_plugin_container(build.find('mvn:plugins', self.namespace))
                    if java_version is not None:
                        return java_version
        return None

    def __find_java_version_in_plugin_container(self, plugins) -> Union[str, None]:
        if plugins is not None:
            for plugin in plugins.findall('mvn:plugin', self.namespace):
                artifactId = plugin.find('mvn:artifactId', self.namespace)
                if artifactId is not None and artifactId.text == 'maven-compiler-plugin':
                    configuration = plugin.find('mvn:configuration', self.namespace)
                    if configuration is not None:
                        source = configuration.find('mvn:source', self.namespace)
                        if source is not None:
                            return self.__resolve_property(source.text)
                        target = configuration.find('mvn:target', self.namespace)
                        if target is not None:
                            return self.__resolve_property(target.text)
        return None
    
    def __set_java_version_in_plugin_container(self, plugins, new_version: str):
        if plugins is not None:
            for plugin in plugins.findall('mvn:plugin', self.namespace):
                artifactId = plugin.find('mvn:artifactId', self.namespace)
                if artifactId is not None and artifactId.text == 'maven-compiler-plugin':
                    configuration = plugin.find('mvn:configuration', self.namespace)
                    if configuration is not None:
                        source = configuration.find('mvn:source', self.namespace)
                        if source is not None:
                            source.text = new_version
                        target = configuration.find('mvn:target', self.namespace)
                        if target is not None:
                            target.text = new_version

    def __save(self):
        if self.pom_path is not None:
            ET.register_namespace('', self.namespace['mvn'])
            self.tree.write(self.pom_path, encoding='utf-8', xml_declaration=True)

    def get_java_version(self) -> Union[str, None]:
        java_version = self.__get_java_version_from_properties()
        
        if java_version is None:
            java_version = self.__get_java_version_from_plugins()

        if java_version is None:
            java_version = self.__get_java_version_from_profiles()
        
        return self.__normalize_java_version(java_version) if java_version is not None else None
    
    def set_java_version(self, new_version: str, save: bool = True):
        new_version = self.__normalize_java_version(new_version)

        if self.properties is not None:
            source = self.properties.find('mvn:maven.compiler.source', self.namespace)
            version = self.properties.find('mvn:java.version', self.namespace)
            if source is not None:
                source.text = new_version
            elif version is not None:
                version.text = new_version
        
        build = self.root.find('mvn:build', self.namespace)
        if build is not None:
            self.__set_java_version_in_plugin_container(build.find('mvn:plugins', self.namespace), new_version)
            plugin_management = build.find('mvn:pluginManagement', self.namespace)
            if plugin_management is not None:
                self.__set_java_version_in_plugin_container(plugin_management.find('mvn:plugins', self.namespace), new_version)

        if save:
            self.__save()

    def get_jar_name(self) -> str:
        artifact_id = self.root.find('mvn:artifactId', self.namespace)
        version = self.root.find('mvn:version', self.namespace)
        build = self.root.find('mvn:build', self.namespace)
        final_name = None

        if build is not None:
            final_name_element = build.find('mvn:finalName', self.namespace)
            if final_name_element is not None:
                final_name = self.__resolve_property(final_name_element.text)

        if final_name:
            jar_name = final_name + '.jar'
        else:
            if artifact_id is not None and version is not None:
                jar_name = f'{self.__resolve_property(artifact_id.text)}-{self.__resolve_property(version.text)}.jar'
            else:
                jar_name = ""

        return jar_name