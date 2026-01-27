#include <bits/stdc++.h>
using namespace std;

inline int charId(char c){
    if(c >= 'A' && c <= 'Z') return c - 'A';
    return 26 + (c - '0');
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    string s1, s2;
    if(!getline(cin, s1)) return 0;
    if(!getline(cin, s2)) return 0;

    const int ALPHA = 36;
    vector<int> pos[ALPHA];
    pos->shrink_to_fit();

    int m = (int)s2.size();
    for(int i = 0; i < m; ++i){
        pos[charId(s2[i])].push_back(i);
    }

    int ptr[ALPHA];
    for(int i = 0; i < ALPHA; ++i) ptr[i] = 0;

    string res;
    res.reserve(min(s1.size(), s2.size()));

    int curr = -1;
    for(char c : s1){
        int id = charId(c);
        auto &v = pos[id];
        int &p = ptr[id];
        while(p < (int)v.size() && v[p] <= curr) ++p;
        if(p < (int)v.size()){
            curr = v[p++];
            res.push_back(c);
        }
    }

    cout << res << '\n';
    return 0;
}