#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    if(!(cin >> t)) return 0;
    while(t--){
        int n;
        cin >> n;
        vector<int> p(n);
        for(int i=0;i<n-1;i++) p[i]=i+2;
        p[n-1]=1;
        for(int i=0;i<n;i++){
            if(i) cout << ' ';
            cout << p[i];
        }
        cout << "\n";
    }
    return 0;
}