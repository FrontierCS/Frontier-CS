#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if(!(cin >> n)) return 0;
    vector<vector<int>> cnt(n, vector<int>(n, 0));
    for (int i = 0; i < n; ++i) {
        for (int k = 0; k < n; ++k) {
            int x; cin >> x; --x;
            cnt[i][x]++;
        }
    }
    auto solid = [&]() {
        for (int i = 0; i < n; ++i) {
            for (int x = 0; x < n; ++x) {
                if (x == i) continue;
                if (cnt[i][x] > 0) return false;
            }
        }
        return true;
    };
    int T = n * (n - 1);
    vector<vector<int>> ops;
    for (int step = 0; step < T && !solid(); ++step) {
        vector<int> send(n, -1);
        // choose cards to send
        for (int i = 0; i < n; ++i) {
            int bestx = -1;
            int bestd = -1;
            // choose a card with x != i to reduce distance, prefer maximum distance
            for (int x = 0; x < n; ++x) if (cnt[i][x] > 0) {
                if (x == i) continue;
                int d = (x - i + n) % n;
                if (d > bestd) {
                    bestd = d;
                    bestx = x;
                }
            }
            if (bestx == -1) {
                // all cards equal to i; must send i
                bestx = i;
            }
            send[i] = bestx;
        }
        // apply simultaneously
        vector<vector<int>> add(n, vector<int>(n, 0));
        for (int i = 0; i < n; ++i) {
            int x = send[i];
            cnt[i][x]--;
            add[(i+1)%n][x]++;
        }
        for (int i = 0; i < n; ++i) {
            for (int x = 0; x < n; ++x) cnt[i][x] += add[i][x];
        }
        // record operation
        vector<int> op(n);
        for (int i = 0; i < n; ++i) op[i] = send[i] + 1;
        ops.push_back(op);
    }
    // If still not solid, attempt remaining steps (up to T) with a simple pass own index to stabilize
    // though likely won't help, but we must respect limit and output whatever we have.
    cout << (int)ops.size() << "\n";
    for (auto &op : ops) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << op[i];
        }
        cout << "\n";
    }
    return 0;
}