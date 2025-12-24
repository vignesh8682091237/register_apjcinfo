import React, { useEffect, useState, useRef } from 'react';
import { StyleSheet, View, Text, Button, FlatList, ActivityIndicator, TextInput, Alert, SafeAreaView } from 'react-native';
import * as SecureStore from 'expo-secure-store';

// Default API URL - change for device/emulator as noted in README
const API_URL = 'http://10.0.2.2:5000/api/registrations';

async function saveKey(key){
  return SecureStore.setItemAsync('api_key', key);
}
async function getKey(){
  return SecureStore.getItemAsync('api_key');
}
async function deleteKey(){
  return SecureStore.deleteItemAsync('api_key');
}

export default function App(){
  const [apiKey, setApiKey] = useState('');
  const [regs, setRegs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [polling, setPolling] = useState(false);
  const pollingRef = useRef(null);

  useEffect(()=>{
    (async ()=>{
      const key = await getKey();
      if(key) setApiKey(key);
    })();
  },[]);

  async function fetchRegs(){
      // use stored access token if available; otherwise exchange api key for token
      let token = await SecureStore.getItemAsync('access_token');
      if(!token){
        const key = await getKey();
        if(!key){
          Alert.alert('Missing API key','Save your API key first');
          return;
        }
        // request token
        try{
          const tres = await fetch('http://10.0.2.2:5000/auth/token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: key })
          });
          if(!tres.ok){
            throw new Error('token request failed ' + tres.status);
          }
          const tjson = await tres.json();
          token = tjson.token;
          await SecureStore.setItemAsync('access_token', token);
        }catch(err){
          Alert.alert('Token error', err.message);
          return;
        }
      }

      setLoading(true);
      try{
        const url = new URL(API_URL);
        const res = await fetch(url.toString(), { headers: { 'Authorization': 'Bearer ' + token }});
        if(res.status === 401){
          // token expired or invalid: remove and retry once
          await SecureStore.deleteItemAsync('access_token');
          return fetchRegs();
        }
        if(!res.ok){
          const txt = await res.text();
          throw new Error('Server error: ' + res.status + '\n' + txt);
        }
        const js = await res.json();
        setRegs(js.registrations || []);
      }catch(err){
        Alert.alert('Fetch error', err.message);
      }finally{
        setLoading(false);
      }
    }

  async function onSaveKey(){
    if(!apiKey) return Alert.alert('Empty','Enter a key');
    await saveKey(apiKey);
    Alert.alert('Saved','API key stored securely');
  }

  async function onClearKey(){
    await deleteKey();
    setApiKey('');
    Alert.alert('Cleared','API key removed');
  }

  useEffect(()=>{
    if(polling){
      // initial fetch then interval
      fetchRegs();
      pollingRef.current = setInterval(fetchRegs, 30000);
    }else{
      if(pollingRef.current){
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    }
    return ()=>{
      if(pollingRef.current){
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    }
  },[polling]);

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Admin Live Registrations</Text>
      </View>

      <View style={styles.controls}>
        <TextInput style={styles.input} placeholder="Paste API key here" value={apiKey} onChangeText={setApiKey} autoCapitalize="none" />
        <View style={styles.row}>
          <Button title="Save Key" onPress={onSaveKey} />
          <View style={{width:10}} />
          <Button title="Clear Key" onPress={onClearKey} color="#d9534f" />
        </View>

        <View style={{height:10}} />
        <View style={styles.row}>
          <Button title="Fetch Now" onPress={fetchRegs} />
          <View style={{width:10}} />
          <Button title={polling? 'Stop Poll' : 'Start Poll'} onPress={() => setPolling(p=>!p)} color={polling? '#6c757d' : '#0d6efd'} />
        </View>
      </View>

      <View style={styles.listWrap}>
        {loading && <ActivityIndicator size="large" />}
        {!loading && (
          <FlatList
            data={regs}
            keyExtractor={(item, idx) => item.Email ? item.Email + idx : String(idx)}
            renderItem={({item, index}) => (
              <View style={styles.item}>
                <Text style={styles.itemTitle}>{item.Name || '—'}</Text>
                <Text style={styles.itemMeta}>{item.Email || ''} • {item.WhatsApp || ''}</Text>
                <Text style={styles.itemMeta}>{item.Qualification || ''} • {item.Designation || ''}</Text>
              </View>
            )}
          />
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex:1, backgroundColor:'#fff'},
  header: { padding:16, borderBottomWidth:1, borderColor:'#eee' },
  title: { fontSize:18, fontWeight:'600' },
  controls: { padding:16 },
  input: { borderWidth:1, borderColor:'#ddd', padding:8, borderRadius:6, marginBottom:8 },
  row: { flexDirection:'row', alignItems:'center' },
  listWrap: { flex:1, padding:8 },
  item: { padding:12, borderBottomWidth:1, borderColor:'#f0f0f0' },
  itemTitle: { fontWeight:'600' },
  itemMeta: { color:'#555', marginTop:4 }
});
