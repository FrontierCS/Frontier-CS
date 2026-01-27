#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read entire input
    string content((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    if (content.empty()) {
        // No input; print nothing or minimal valid output
        cout << 0 << "\n\n";
        return 0;
    }
    istringstream iss(content);
    vector<long long> nums;
    long long v;
    while (iss >> v) nums.push_back(v);

    if (nums.empty()) {
        cout << 0 << "\n\n";
        return 0;
    }

    int n = (int)nums[0];
    if (n <= 0) {
        cout << 0 << "\n\n";
        return 0;
    }

    vector<int> a(n + 1, 0);
    if ((int)nums.size() >= n + 1) {
        for (int i = 1; i <= n; ++i) {
            long long val = nums[i];
            if (val < 1 || val > n) {
                // Fallback to identity if invalid (shouldn't happen in valid input)
                a[i] = i;
            } else {
                a[i] = (int)val;
            }
        }
    } else {
        // Not enough data; fallback to identity mapping
        for (int i = 1; i <= n; ++i) a[i] = i;
    }

    // Build reverse graph
    vector<vector<int>> rev(n + 1);
    for (int i = 1; i <= n; ++i) {
        rev[a[i]].push_back(i);
    }

    // Compute forward orbit of 1
    vector<char> inOrbit(n + 1, 0);
    vector<int> seeds;
    int u = 1;
    while (!inOrbit[u]) {
        inOrbit[u] = 1;
        seeds.push_back(u);
        u = a[u];
    }

    // Reverse BFS from the orbit to find all nodes that can reach it
    vector<char> can(n + 1, 0);
    queue<int> q;
    for (int s : seeds) {
        can[s] = 1;
        q.push(s);
    }
    while (!q.empty()) {
        int cur = q.front(); q.pop();
        for (int pre : rev[cur]) {
            if (!can[pre]) {
                can[pre] = 1;
                q.push(pre);
            }
        }
    }

    vector<int> ans;
    for (int i = 1; i <= n; ++i) if (can[i]) ans.push_back(i);

    cout << ans.size();
    if (!ans.empty()) {
        cout << ' ';
        for (size_t i = 0; i < ans.size(); ++i) {
            if (i) cout << ' ';
            cout << ans[i];
        }
    }
    cout << "\n";
    return 0;
}