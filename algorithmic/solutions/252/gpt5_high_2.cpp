#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<long long> tokens;
    long long val;
    while (cin >> val) tokens.push_back(val);
    if (tokens.empty()) return 0;
    
    int n = (int)tokens[0];
    vector<int> a(n + 1);
    if ((int)tokens.size() >= 1 + n) {
        for (int i = 1; i <= n; ++i) a[i] = (int)tokens[i];
    } else {
        for (int i = 1; i <= n; ++i) a[i] = i;
    }

    vector<int> term(n + 1, -1);
    vector<int> seenRun(n + 1, 0), step(n + 1, 0);
    int run = 0, cycCount = 0;

    for (int u = 1; u <= n; ++u) {
        if (term[u] != -1) continue;
        ++run;
        vector<int> path;
        int v = u;
        while (true) {
            if (term[v] != -1) {
                int t = term[v];
                for (int w : path) term[w] = t;
                break;
            }
            if (seenRun[v] == run) {
                int cycleStart = step[v];
                int t = cycCount++;
                for (int i = cycleStart; i < (int)path.size(); ++i) term[path[i]] = t;
                for (int i = 0; i < cycleStart; ++i) term[path[i]] = t;
                break;
            }
            seenRun[v] = run;
            step[v] = (int)path.size();
            path.push_back(v);
            v = a[v];
        }
    }

    int target = term[1];
    vector<int> ans;
    for (int i = 1; i <= n; ++i) if (term[i] == target) ans.push_back(i);
    sort(ans.begin(), ans.end());
    
    cout << "! " << ans.size();
    for (int x : ans) cout << " " << x;
    cout << "\n";
    return 0;
}