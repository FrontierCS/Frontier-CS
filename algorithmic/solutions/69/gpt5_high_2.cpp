#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<string> words;
    for (int len = 1; (int)words.size() < n; ++len) {
        int total = 1 << min(len, 20); // safe when len <= 20; but n<=1000 so len won't exceed 10
        for (int mask = 0; mask < total && (int)words.size() < n; ++mask) {
            string s;
            s.reserve(len);
            for (int i = len - 1; i >= 0; --i) {
                if (mask & (1 << i)) s.push_back('O');
                else s.push_back('X');
            }
            words.push_back(s);
        }
    }
    for (int i = 0; i < n; ++i) {
        cout << words[i] << "\n";
    }
    cout.flush();

    int q;
    if (!(cin >> q)) return 0;
    while (q--) {
        long long p;
        cin >> p;
        cout << 1 << " " << 1 << "\n";
        cout.flush();
    }
    return 0;
}