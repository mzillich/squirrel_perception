/*
 * squirrel_attention_symmetry.cpp
 *
 *  Created on: Nov 6, 2014
 *      Author: Ekaterina Potapova
 */

#include <squirrel_attention/squirrel_attention_symmetry.hpp>

bool 
AttentionSymmetryService::calculate (squirrel_object_perception_msgs::GetSaliencySymmetry::Request & req, squirrel_object_perception_msgs::GetSaliencySymmetry::Response & response)
{
  pcl::PointCloud<PointT>::Ptr scene (new pcl::PointCloud<PointT>);
  pcl::fromROSMsg (req.cloud, *scene);
  
  //get pimage from point cloud
  cv::Mat RGB;
  getImageFromPointCloud(scene,RGB);
  
  // start creating parameters
  saliencyMap_.reset(new AttentionModule::SymmetryMap);
  saliencyMap_->setImage(RGB);
  //saliencyMap_->setWidth(scene->width);
  //saliencyMap_->setHeight(scene->height);
  
  saliencyMap_->calculatePyramid();
  
  cv::Mat map;
  if(!(saliencyMap_->getMap(map)))
  {
    return(false);
  }
//  cv::imshow("map",map);
//  cv::waitKey(-1);
  
  resize(map,map,cv::Size(scene->width,scene->height));
  map.convertTo(map,CV_8U,255);

  cv_bridge::CvImagePtr cv_ptr(new cv_bridge::CvImage);
  ros::Time time = ros::Time::now();
  // convert OpenCV image to ROS message
  cv_ptr->header.stamp = time;
  cv_ptr->header.frame_id = "image";
  cv_ptr->encoding = "mono8";
  cv_ptr->image = map;
    
  //sensor_msgs::Image im;
  cv_ptr->toImageMsg(response.saliency_map);
  return(true);
}

void
AttentionSymmetryService::initialize (int argc, char ** argv)
{
  ros::init (argc, argv, "squirrel_attention_symmetry_server");
  n_ = new ros::NodeHandle ();
    
  attention_ = n_->advertiseService ("/squirrel_attention_symmetry", &AttentionSymmetryService::calculate, this);
  ROS_INFO("Ready to get service calls...");
  ros::spin ();
}

int
main (int argc, char ** argv)
{
  AttentionSymmetryService m;
  m.initialize (argc, argv);

  return 0;
}