cmake_minimum_required(VERSION 3.8)
project(h1_description)

find_package(ament_cmake REQUIRED)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(h1_visual_assets test/test_visual_assets.py)
endif()

install(DIRECTORY meshes urdf
  DESTINATION share/${PROJECT_NAME}
)

install(FILES ASSET_SHA256SUMS LICENSE MODEL_ASSET_NOTICE.md
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
