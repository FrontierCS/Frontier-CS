#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        if (!(cin >> n)) return 0;
        vector<char> types;
        types.reserve(n);
        string tok;
        while ((int)types.size() < n && (cin >> tok)) {
            bool allNSdash = !tok.empty();
            for (char c : tok) {
                if (c != 'N' && c != 'S' && c != '-') {
                    allNSdash = false;
                    break;
                }
            }
            if (allNSdash) {
                for (char c : tok) {
                    if ((int)types.size() < n) types.push_back(c);
                }
                continue;
            }
            if (tok.size() == 1) {
                char c = tok[0];
                if (c == 'N' || c == 'S' || c == '-') {
                    types.push_back(c);
                    continue;
                }
                if (c == '0') { types.push_back('-'); continue; }
                if (c == '1') { types.push_back('N'); continue; }
                if (c == '2') { types.push_back('S'); continue; }
            }
            // Try to extract valid characters from within the token
            for (char c : tok) {
                if ((int)types.size() >= n) break;
                if (c == 'N' || c == 'S' || c == '-') {
                    types.push_back(c);
                }
            }
        }
        // If still not enough, pad with '-' as fallback (unlikely, but to avoid out-of-bounds)
        while ((int)types.size() < n) types.push_back('-');
        
        vector<int> ans;
        for (int i = 0; i < n; ++i) if (types[i] == '-') ans.push_back(i + 1);
        cout << ans.size();
        for (int idx : ans) cout << " " << idx;
        cout << "\n";
    }
    return 0;
}