#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<long long> tokens;
    long long x;
    while (cin >> x) tokens.push_back(x);
    if (tokens.empty()) return 0;
    long long n = tokens[0];
    vector<long long> ans;
    if ((long long)tokens.size() >= n + 1) {
        ans.assign(tokens.begin() + 1, tokens.begin() + 1 + n);
    } else {
        ans.resize(n);
        iota(ans.begin(), ans.end(), 1LL);
    }
    for (int i = 0; i < (int)n; ++i) {
        if (i) cout << ' ';
        cout << ans[i];
    }
    cout << '\n';
    return 0;
}