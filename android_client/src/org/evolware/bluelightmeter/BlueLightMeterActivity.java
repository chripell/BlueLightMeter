/*
Copyright 2016 Google Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package org.evolware.bluelightmeter;

import android.app.Activity;
import android.util.Log;
import android.os.Bundle;
import android.view.View;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.content.pm.PackageManager;
import android.widget.Toast;
import org.evolware.bluelightmeter.BlueLightMeterDriver;
import org.evolware.bluelightmeter.BlueLightMeterData;

public class BlueLightMeterActivity extends Activity
{
    private static final String TAG = "BLMActivity";
    private BlueLightMeterData blmData;
    private BlueLightMeterDriver blmDriver;
    
    /** Called when the activity is first created. */
    @Override
    public void onCreate(Bundle savedInstanceState)
    {
	Log.i(TAG, "onCreate");
	super.onCreate(savedInstanceState);
        setContentView(R.layout.main);

	blmDriver = new BlueLightMeterDriver(this);
	blmData = blmDriver.getData();
	
        WebView mainWebView = (WebView) findViewById(R.id.mainWebView);

	// TODO: disable
	mainWebView.setWebContentsDebuggingEnabled(true);
	
        WebSettings webSettings = mainWebView.getSettings();
        webSettings.setJavaScriptEnabled(true);
     
        mainWebView.addJavascriptInterface(blmData, "BLM");
        mainWebView.setScrollBarStyle(View.SCROLLBARS_INSIDE_OVERLAY);
        mainWebView.loadUrl("file:///android_asset/blm.html");
    }

    // Connect and disconnect on Activity Resume/Pause to spare
    // battery on RFDuino.
    @Override
    public void onResume()
    {
	Log.i(TAG, "onResume");
	super.onResume();
	blmDriver.initDevice();
    }

    @Override
    public void onPause()
    {
	Log.i(TAG, "onPause");
	super.onPause();
	blmDriver.closeDevice();
    }
}
