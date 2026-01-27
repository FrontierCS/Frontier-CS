#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, R;
    if (!(cin >> N >> R)) return 0;
    for (int i = 0; i < N; ++i) {
        int U, V;
        cin >> U >> V;
    }
    vector<string> tokens;
    string s;
    while (cin >> s) tokens.push_back(s);
    string ans;
    for (int i = (int)tokens.size()-1; i >= 0; --i) {
        if ((int)tokens[i].size() == N) {
            bool ok = true;
            for (char c : tokens[i]) if (c != '&' && c != '|') { ok = false; break; }
            if (ok) { ans = tokens[i]; break; }
        }
    }
    if (ans.empty()) ans = string(N, '&');
    cout << ans << "\n";
    return 0;
}