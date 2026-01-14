#include <bits/stdc++.h>
using namespace std;

int query(int a, int b, int c) {
    cout << "0 " << a << " " << b << " " << c << endl;
    cout.flush();
    int res;
    cin >> res;
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int n;
    cin >> n;

    if (n == 3) {
        int m = query(1, 2, 3);
        if (m == 1) {
            cout << "1 1 2 1 3" << endl;
        } else if (m == 2) {
            cout << "1 1 2 2 3" << endl;
        } else {
            cout << "1 1 3 2 3" << endl;
        }
        cout.flush();
        return 0;
    }

    vector<int> parent(n + 1, 0);
    vector<vector<int>> children(n + 1);
    vector<int> leaves;

    // Build initial tree with nodes 1,2,3
    int m = query(1, 2, 3);
    if (m == 1) {
        parent[2] = 1;
        parent[3] = 1;
        children[1].push_back(2);
        children[1].push_back(3);
        leaves.push_back(2);
        leaves.push_back(3);
    } else if (m == 2) {
        parent[2] = 1;
        parent[3] = 2;
        children[1].push_back(2);
        children[2].push_back(3);
        leaves.push_back(3);
    } else { // m == 3
        parent[3] = 1;
        parent[2] = 3;
        children[1].push_back(3);
        children[3].push_back(2);
        leaves.push_back(2);
    }

    // Process nodes 4..n
    for (int i = 4; i <= n; ++i) {
        // Select up to 20 leaves (excluding node 1)
        vector<int> candidates;
        for (int leaf : leaves) {
            if (leaf != 1) {
                candidates.push_back(leaf);
                if (candidates.size() >= 20) break;
            }
        }

        map<int, int> cnt;
        for (int leaf : candidates) {
            int res = query(1, i, leaf);
            cnt[res]++;
        }

        // Choose the node with highest frequency (excluding 1 and i)
        int best = -1, best_cnt = -1;
        for (auto &p : cnt) {
            if (p.first == 1 || p.first == i) continue;
            if (p.second > best_cnt) {
                best_cnt = p.second;
                best = p.first;
            }
        }

        if (best == -1) {
            // Default to root
            best = 1;
        }

        parent[i] = best;
        children[best].push_back(i);

        // Update leaves: remove parent if it was a leaf, add i
        auto it = find(leaves.begin(), leaves.end(), best);
        if (it != leaves.end()) leaves.erase(it);
        leaves.push_back(i);
    }

    // Output the tree edges
    cout << "1";
    for (int i = 2; i <= n; ++i) {
        cout << " " << parent[i] << " " << i;
    }
    cout << endl;
    cout.flush();

    return 0;
}