package org.evolware.bluelightmeter;

import android.content.Context;
import android.hardware.SensorManager;
import android.hardware.Sensor;
import android.hardware.SensorEventListener;
import android.hardware.SensorEvent;
import android.webkit.JavascriptInterface;
import org.evolware.bluelightmeter.BlueLightMeterSetterGetter;

public class BlueLightMeterData implements SensorEventListener {
    private BlueLightMeterSetterGetter setterGetter;
    private String status = "DEFAULT";
    private int mode = 0;
    public static final int MODE_UNKNOWN = 0;
    public static final int MODE_BLM = 1;
    public static final int MODE_KO = 2;

    private SensorManager mSensorManager;
    private Sensor mLux;
    private float lux = -1.0F;
    
    public synchronized void setStatus(String status) {
	this.status = status;
    }

    public synchronized void setMode(int mode) {
	this.mode = mode;
    }
    
    @JavascriptInterface
    public synchronized String getStatus() {
	return status;
    }

    @JavascriptInterface
    public synchronized String getData() {
	if (mode == MODE_UNKNOWN) {
	    return "initializing:";
	}
	if (mode == MODE_BLM) {
	    return setterGetter.getValue();
	}
	if (lux >= 0.0) {
	    return "lux: " + Float.toString(lux);
	}
	return "nolux:";
    }

    @JavascriptInterface
    public synchronized float getLux() {
	return lux;
    }
    
    @JavascriptInterface
    public synchronized int getMode() {
	return mode;
    }

    @JavascriptInterface
    public synchronized void setParameters(String par) {
	if (mode == MODE_BLM) {
	    setterGetter.setParameters(par);
	}
    }
    
    public BlueLightMeterData(BlueLightMeterSetterGetter setterGetter, Context context) {
	this.setterGetter = setterGetter;
	mSensorManager = (SensorManager) context.getSystemService(Context.SENSOR_SERVICE);
	mLux = mSensorManager.getDefaultSensor(Sensor.TYPE_LIGHT);
    }

    public synchronized void init() {
	if (mLux != null) {
	    mSensorManager.registerListener(this, mLux, SensorManager.SENSOR_DELAY_UI);
	}
    }

    public synchronized void close() {
	if (mLux != null) {
	    mSensorManager.unregisterListener(this);
	}
    }

    @Override
    public final void onSensorChanged(SensorEvent event) {
	lux = event.values[0];
    }

    @Override
    public final void onAccuracyChanged(Sensor sensor, int accuracy) {
    }
}
