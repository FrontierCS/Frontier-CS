#include <bits/stdc++.h>
using namespace std;

int identify(int u, int k, int n) {
    int low = 1, high = n;
    while (low < high) {
        int mid = (low + high) / 2;
        int sz = mid - low + 1;
        cout << "? " << u << " " << k << " " << sz;
        for (int i = low; i <= mid; ++i) {
            cout << " " << i;
        }
        cout << endl << flush;
        int ans;
        cin >> ans;
        if (ans) {
            high = mid;
        } else {
            low = mid + 1;
        }
    }
    return low;
}

int main() {
    int n;
    cin >> n;
    vector<int> a(n + 1);
    for (int u = 1; u <= n; ++u) {
        a[u] = identify(u, 1, n);
    }
    // Find reachable from 1
    set<int> reach;
    vector<bool> vis(n + 1, false);
    int cur = 1;
    while (!vis[cur]) {
        vis[cur] = true;
        reach.insert(cur);
        cur = a[cur];
    }
    // Now find A
    vector<int> ans;
    for (int x = 1; x <= n; ++x) {
        int curr = x;
        bool can_reach = false;
        set<int> seen; // to prevent infinite loop, though n small
        for (int step = 0; step <= n; ++step) {
            if (reach.count(curr)) {
                can_reach = true;
                break;
            }
            if (seen.count(curr)) break;
            seen.insert(curr);
            curr = a[curr];
        }
        if (can_reach) {
            ans.push_back(x);
        }
    }
    // Output
    cout << "! " << ans.size();
    for (int x : ans) {
        cout << " " << x;
    }
    cout << endl << flush;
    return 0;
}