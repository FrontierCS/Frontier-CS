#include <bits/stdc++.h>
using namespace std;

void solve() {
    int n;
    cin >> n;
    set<string> words;
    for (char c = 'a'; c <= 'z'; ++c) {
        if ((int)words.size() >= n) break;
        int k = 1;
        while (true) {
            if ((int)words.size() >= n) break;
            cout << "query " << string(1, c) << " " << k << endl;
            cout.flush();
            int cnt;
            cin >> cnt;
            vector<string> res(cnt);
            for (int i = 0; i < cnt; ++i) cin >> res[i];
            for (const string& w : res) words.insert(w);
            if (cnt < k) break;
            k = min(k * 2, n);
        }
    }
    cout << "answer ";
    for (const string& w : words) cout << w << " ";
    cout << endl;
}

int main() {
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}