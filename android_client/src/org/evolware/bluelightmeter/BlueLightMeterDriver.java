package org.evolware.bluelightmeter;

import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothGatt;
import android.bluetooth.BluetoothGattCallback;
import android.bluetooth.BluetoothGattCharacteristic;
import android.bluetooth.BluetoothGattDescriptor;
import android.bluetooth.BluetoothGattService;
import android.bluetooth.BluetoothManager;
import android.bluetooth.BluetoothProfile;
import android.content.Context;
import android.content.Intent;
import android.os.Handler;
import android.util.Log;
import android.widget.Toast;
import android.content.pm.PackageManager;
import java.io.UnsupportedEncodingException;
import org.evolware.bluelightmeter.BlueLightMeterData;
import org.evolware.bluelightmeter.BlueLightMeterSetterGetter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.UUID;


public class BlueLightMeterDriver implements BlueLightMeterSetterGetter {
    private static final String TAG = "BLMDriver";
    private static final String RFDUINO_READ = "00002221-0000-1000-8000-00805f9b34fb";
    private static final String RFDUINO_WRITE = "00002222-0000-1000-8000-00805f9b34fb";
    private static final String RFDUINO_SERVICE = "00002220-0000-1000-8000-00805f9b34fb";

    private BlueLightMeterData data = null;
    private BluetoothAdapter mBluetoothAdapter = null;
    private Activity mContext;
    private boolean mScanning;
    private Handler mHandler;
    private boolean writePending = false;
    private BluetoothAdapter.LeScanCallback mLeScanCallback;
    private BluetoothDevice device;
    private BluetoothGatt mBluetoothGatt;
    private BluetoothGattCharacteristic writeCharacteristic;
    private BluetoothGattCharacteristic readCharacteristic;
    private int mConnectionState = STATE_DISCONNECTED;

    private static final int STATE_DISCONNECTED = 0;
    private static final int STATE_CONNECTING = 1;
    private static final int STATE_CONNECTED = 2;

    // Stops scanning after 10 seconds.
    private static final long SCAN_PERIOD = 10000;

    private final BluetoothGattCallback mGattCallback = new BluetoothGattCallback() {
        @Override
        public void onConnectionStateChange(BluetoothGatt gatt, int status, int newState) {
            if (newState == BluetoothProfile.STATE_CONNECTED) {
		data.setStatus("BLM connected");
                mConnectionState = STATE_CONNECTED;
                Log.i(TAG, "Connected to GATT server " + mBluetoothGatt.discoverServices());
            } else if (newState == BluetoothProfile.STATE_DISCONNECTED) {
		setKO("BLM disconnected");
                mConnectionState = STATE_DISCONNECTED;
            }
        }

        @Override
        public void onServicesDiscovered(BluetoothGatt gatt, int status) {
	    Log.i(TAG, "onServicesDiscovered received: " + status);
	    if (status == BluetoothGatt.GATT_SUCCESS) {
		data.setMode(BlueLightMeterData.MODE_BLM);
		List<BluetoothGattService> gattServices = mBluetoothGatt.getServices();
		for (BluetoothGattService s: gattServices) {
		    List<BluetoothGattCharacteristic> gattCharacteristics = s.getCharacteristics();
		    for (BluetoothGattCharacteristic c: gattCharacteristics) {
			String uuid = c.getUuid().toString();
			Log.i(TAG, "Cahrateristic: " + uuid);
			if (uuid.equals(RFDUINO_READ)) {
			    Log.i(TAG, "Enabling read notification: " + uuid);
			    readCharacteristic = c;
			    mBluetoothGatt.readCharacteristic(c);
			}
			if (uuid.equals(RFDUINO_WRITE)) {
			    Log.i(TAG, "Saving write characteristic: " + uuid);
			    Log.i(TAG, "Service UUID is: " + c.getService().getUuid());
			    writeCharacteristic = c;
			}
		    }
		}
	    }
	    else {
		setKO("onServicesDiscovered received: " + status);
	    }
        }

        @Override
        public void onCharacteristicRead(BluetoothGatt gatt,
                                         BluetoothGattCharacteristic characteristic,
                                         int status) {
	    if (status == BluetoothGatt.GATT_SUCCESS) {
		readCharacteristic = characteristic;
	    }
	    else {
		setKO("onCharacteristicRead received: " + status);
	    }
	    if (writePending) {
		writePending = false;
		if (!mBluetoothGatt.writeCharacteristic(writeCharacteristic)) {
		    setKO("write characteristic write failed");
		}
	    }
        }

        @Override
        public void onCharacteristicChanged(BluetoothGatt gatt,
                                            BluetoothGattCharacteristic characteristic) {
	    Log.i(TAG, "onCharacteristicChanged received");
        }
	    
        @Override
        public void onCharacteristicWrite(BluetoothGatt gatt,
					  BluetoothGattCharacteristic characteristic,
					  int status) {
	    Log.i(TAG, "onCharacteristicWrite received: " + status);
        }
    };

    private void setKO(String reason) {
	    Log.e(TAG, reason);
	    data.setStatus(reason);
	    data.setMode(BlueLightMeterData.MODE_KO);
    }
    
    private void scanLeDevice(final boolean enable) {      	
        if (enable && !mScanning) {
	    Log.i(TAG, "Starting Scan");
            // Stops scanning after a pre-defined scan period.
            mHandler.postDelayed(new Runnable() {
                @Override
                public void run() {
		    Log.i(BlueLightMeterDriver.TAG, "Scan Timeout");
		    scanLeDevice(false);
		    if (mBluetoothGatt == null) {
			setKO("NO BlueLightMeter found");
		    }
                }
            }, SCAN_PERIOD);

            mScanning = true;
            mBluetoothAdapter.startLeScan(mLeScanCallback);
        }
	if (!enable && mScanning) {
	    Log.i(TAG, "Stopping Scan");
            mScanning = false;
            mBluetoothAdapter.stopLeScan(mLeScanCallback);
        }
    }

    private void connectDevice(BluetoothDevice device) {
	this.device = device;
	mBluetoothGatt = device.connectGatt(mContext, false, mGattCallback);
    }

    private BluetoothDevice getDevice() {
	return this.device;
    }

    public void initDevice() {
	Log.i(TAG, "Init");
	data.init();
	if (device != null) {
	    Log.i(TAG, "Device Cached");
	    connectDevice(device);
	    return;
	}
	
	if (!mContext.getPackageManager().hasSystemFeature(PackageManager.FEATURE_BLUETOOTH_LE)) {
	    setKO("BLE not available");
	    return;
	}

	final BluetoothManager bluetoothManager =
	    (BluetoothManager) mContext.getSystemService(Context.BLUETOOTH_SERVICE);
	this.mBluetoothAdapter = bluetoothManager.getAdapter();
	if (this.mBluetoothAdapter == null || !this.mBluetoothAdapter.isEnabled()) {
	    setKO("Bluetooth turned off");
	    return;
	}
	scanLeDevice(true);
    }

    public void closeDevice() {
	Log.i(TAG, "Closing");
	data.close();
	scanLeDevice(false);
	if (mBluetoothGatt != null) {
	    Log.i(TAG, "Disconnecting Gatt");
	    mBluetoothGatt.close();
	    mBluetoothGatt = null;
        }

    }

    public void setParameters(String par) {
	String[] parts = par.split(" ");
	byte[] val = new byte[parts.length];
	for(int i = 0; i < parts.length; i++) {
	    val[i] = (byte) Short.parseShort(parts[i], 16);
	}
	if (writeCharacteristic.setValue(val)) {
	    writePending = true;
	}
	else {
	    setKO("write characteristic set value failed");
	}
    }

    public String getValue() {
	if (readCharacteristic == null)
	    return "nodata:";
	byte[] val = readCharacteristic.getValue();
	if (val != null && val.length > 0) {
	    final StringBuilder stringBuilder = new StringBuilder(val.length + 1);
	    stringBuilder.append("blm: ");
	    for(byte byteChar : val)
		stringBuilder.append(String.format("%02X ", byteChar));
	    if (mBluetoothGatt != null) {
		mBluetoothGatt.readCharacteristic(readCharacteristic);
	    }
	    return stringBuilder.toString();
	}
	return "nodata:";
    }
    
    BlueLightMeterDriver(Activity mContext) {
	this.mContext = mContext;
	mHandler = new Handler();
	data = new BlueLightMeterData(this, mContext);
	// Device scan callback.
	final Activity fmContext = mContext;
	mLeScanCallback =
	    new BluetoothAdapter.LeScanCallback() {
		@Override
		public void onLeScan(final BluetoothDevice device, int rssi,
				     final byte[] scanRecord) {
		    fmContext.runOnUiThread(new Runnable() {
			    @Override
			    public void run() {
				String decoded = "Found Device " + device.getAddress() + ": ";
				try {
				    decoded += new String(scanRecord, "UTF-8");
				} catch (UnsupportedEncodingException e)  {
				    decoded += "Unsupported encoding";
				}
				Log.i(BlueLightMeterDriver.TAG, decoded);
				if (getDevice() == null && decoded.contains("RFduino") && decoded.contains("BlueL")) {
				    Log.i(TAG, "Stopping Scan because found");
				    scanLeDevice(false);
				    String found = "Found BLM: " + device.getAddress();
				    Log.i(BlueLightMeterDriver.TAG, found);
				    data.setStatus(found);
				    connectDevice(device);
				}
			    }
			});
		}
	    };
    }

    public BlueLightMeterData getData() {
	return data;
    }
}
