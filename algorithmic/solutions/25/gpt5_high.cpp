#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if(!(cin >> T)) return 0;
    for(int _=0;_<T;_++){
        int n;
        if(!(cin >> n)) return 0;
        if(n <= 0){
            cout << "! 1" << endl;
            cout.flush();
            continue;
        }
        bool disconnected = false;
        for(int i=0;i<n;i++){
            string s(n,'0');
            s[i]='1';
            cout << "? " << s << endl;
            cout.flush();
            int ans;
            if(!(cin >> ans)) return 0;
            if(n>1 && ans==0) disconnected = true;
        }
        cout << "! " << (disconnected?0:1) << endl;
        cout.flush();
    }
    return 0;
}