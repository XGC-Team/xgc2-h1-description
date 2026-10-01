cmake_minimum_required(VERSION 3.0.2)
project(h1_description)

find_package(catkin REQUIRED)

catkin_package()

if(CATKIN_ENABLE_TESTING)
  catkin_add_nosetests(test/test_visual_assets.py)
endif()

install(DIRECTORY meshes urdf
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)

install(FILES ASSET_SHA256SUMS LICENSE MODEL_ASSET_NOTICE.md
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
