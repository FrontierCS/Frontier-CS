#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    cin >> t;
    for (int test = 0; test < t; ++test) {
        int n, m;
        cin >> n >> m;
        vector<pair<int, int>> roads(m + 1);
        for (int i = 1; i <= m; ++i) {
            int a, b;
            cin >> a >> b;
            roads[i] = {a, b};
        }
        // Block all roads
        for (int i = 1; i <= m; ++i) {
            cout << "- " << i << endl;
            cout.flush();
        }
        // Find s
        int s = -1;
        for (int y = 1; y <= n; ++y) {
            cout << "? 1 " << y << endl;
            cout.flush();
            int res;
            cin >> res;
            if (res == -1) return 0;
            if (res == 1) {
                s = y;
                break;
            }
        }
        assert(s != -1);
        // Now s found, all blocked
        vector<bool> in_R(n + 1, false);
        in_R[s] = true;
        vector<bool> is_repaired(m + 1, false);
        vector<bool> tested(m + 1, false);
        vector<int> tree_edge(n + 1, 0);
        // Initial batch for direct neighbors
        vector<int> initial_batch;
        for (int i = 1; i <= m; ++i) {
            int a = roads[i].first, b = roads[i].second;
            if ((a == s && in_R[b]) || (b == s && in_R[a])) continue;
            int v = (a == s ? b : a);
            if (in_R[v]) continue;
            tested[i] = true;
            cout << "+ " << i << endl;
            cout.flush();
            cout << "? 1 " << v << endl;
            cout.flush();
            int res;
            cin >> res;
            if (res == -1) return 0;
            cout << "- " << i << endl;
            cout.flush();
            bool rep = (res == 1);
            is_repaired[i] = rep;
            if (rep) {
                in_R[v] = true;
                initial_batch.push_back(v);
                tree_edge[v] = i;
                cout << "+ " << i << endl;
                cout.flush();
            }
        }
        // Now process initial batch if any
        vector<vector<int>> batches;
        if (!initial_batch.empty()) {
            batches.push_back(initial_batch);
        }
        // Now the do while for further
        bool added = true;
        while (added) {
            added = false;
            vector<int> new_batch;
            for (int i = 1; i <= m; ++i) {
                if (tested[i]) continue;
                int a = roads[i].first, b = roads[i].second;
                bool ain = in_R[a], bin = in_R[b];
                if (ain == bin) continue;  // both in or both out
                tested[i] = true;
                int uu = ain ? a : b;
                int ww = ain ? b : a;
                cout << "+ " << i << endl;
                cout.flush();
                cout << "? 1 " << ww << endl;
                cout.flush();
                int res;
                cin >> res;
                if (res == -1) return 0;
                cout << "- " << i << endl;
                cout.flush();
                bool rep = (res == 1);
                is_repaired[i] = rep;
                if (rep && !in_R[ww]) {
                    in_R[ww] = true;
                    new_batch.push_back(ww);
                    tree_edge[ww] = i;
                    added = true;
                    cout << "+ " << i << endl;
                    cout.flush();
                }
            }
            if (!new_batch.empty()) {
                batches.push_back(new_batch);
            }
        }
        // Now process all batches for intra edges
        for (auto& batch : batches) {
            if (batch.empty()) continue;
            // Block all tree edges to this batch
            for (int w : batch) {
                cout << "- " << tree_edge[w] << endl;
                cout.flush();
            }
            // Now test intra
            unordered_set<int> batch_set(batch.begin(), batch.end());
            for (int i = 1; i <= m; ++i) {
                if (tested[i]) continue;
                int a = roads[i].first, b = roads[i].second;
                if (batch_set.count(a) && batch_set.count(b)) {
                    tested[i] = true;
                    int w1 = a, w2 = b;  // arbitrary
                    if (tree_edge[w1] == 0) swap(w1, w2);  // ensure w1 has tree edge
                    cout << "+ " << tree_edge[w1] << endl;
                    cout.flush();
                    cout << "+ " << i << endl;
                    cout.flush();
                    cout << "? 1 " << w2 << endl;
                    cout.flush();
                    int res;
                    cin >> res;
                    if (res == -1) return 0;
                    cout << "- " << i << endl;
                    cout.flush();
                    cout << "- " << tree_edge[w1] << endl;
                    cout.flush();
                    is_repaired[i] = (res == 1);
                }
            }
            // Unblock the tree edges
            for (int w : batch) {
                cout << "+ " << tree_edge[w] << endl;
                cout.flush();
            }
        }
        // Now output
        cout << "!";
        for (int i = 1; i <= m; ++i) {
            cout << " " << is_repaired[i];
        }
        cout << endl;
        cout.flush();
        int verdict;
        cin >> verdict;
        if (verdict == -1 || verdict == 0) return 0;
    }
    return 0;
}