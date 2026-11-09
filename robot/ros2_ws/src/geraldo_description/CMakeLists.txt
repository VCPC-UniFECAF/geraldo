cmake_minimum_required(VERSION 3.8)
project(geraldo_description)

find_package(ament_cmake REQUIRED)

install(DIRECTORY urdf meshes launch config worlds
  DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_urdf test/test_urdf.py)
  ament_add_pytest_test(test_launch_files test/test_launch_files.py)
endif()

ament_package()
