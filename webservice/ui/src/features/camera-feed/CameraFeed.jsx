import React from "react";
import "./CameraFeed.css";
import { HTTP, SETTINGS } from "../../constants/constants";

class CameraFeed extends React.Component {
  constructor( props ) {
    super( props );
    this.mjpgSrc = HTTP.CAMERA_FEED;
    this.refreshImage = this.refreshImage.bind( this );
    this.mjpgSrc = HTTP.CAMERA_FEED;

    this.state = {
      mjpgSrc: this.mjpgSrc,
    };
  }
  refreshImage() {
    const d = new Date();
    this.setState( { mjpgSrc: `${ this.mjpgSrc }?ver=${ d.getTime() }` } );
  }

  autoRefresh(source) {
    setInterval(function() {
      var ver = new Date().getTime();
      document.getElementById('camera').setAttribute('src', source+'?ver=' + ver);
    }, 2000)
  }

  render() {
    const width = SETTINGS.CAMERA_FEED_WIDTH;//640
    const imgStyle = { "maxWidth": `${ width }px` };
    return (
      <div className="camera-feed" >
        <div className="camera-feed-container">
          <img src={ this.state.mjpgSrc } alt="camera feed" style={ imgStyle } className="camera-feed-img" id="camera" onLoad={ this.autoRefresh(this.state.mjpgSrc) } />
        </div>
      </div>
    );
  }
}

export default CameraFeed;
