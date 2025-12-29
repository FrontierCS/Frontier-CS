#include <bits/stdc++.h>
using namespace std;

void query(const vector<int>& ops, vector<int>& res) {
    int L = ops.size();
    cout << L;
    for (int v : ops) cout << " " << v;
    cout << endl;
    cout.flush();
    res.resize(L);
    for (int i = 0; i < L; ++i) {
        cin >> res[i];
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int subtask, n;
    cin >> subtask >> n;

    vector<bool> used(n + 1, false);
    used[1] = true;

    // Find one neighbor of node 1
    vector<int> ops;
    for (int b = 2; b <= n; ++b) {
        ops.push_back(1);
        ops.push_back(b);
        ops.push_back(1);
        ops.push_back(b);
    }
    vector<int> res;
    query(ops, res);

    int neighbor = -1;
    for (int i = 0; i < n - 1; ++i) {
        if (res[4 * i + 1] == 1) {
            neighbor = 2 + i;
            break;
        }
    }
    // neighbor must exist
    used[neighbor] = true;

    deque<int> chain;
    chain.push_back(1);
    chain.push_back(neighbor);
    int left = chain.front();
    int right = chain.back();

    // Process remaining nodes
    for (int x = 2; x <= n; ++x) {
        if (used[x]) continue;
        ops.clear();
        // test adjacency with left
        ops.push_back(left); ops.push_back(x); ops.push_back(left); ops.push_back(x);
        // test adjacency with right
        ops.push_back(right); ops.push_back(x); ops.push_back(right); ops.push_back(x);
        query(ops, res);

        bool adj_left = res[1];
        bool adj_right = res[5];

        if (adj_left) {
            chain.push_front(x);
            left = x;
        } else if (adj_right) {
            chain.push_back(x);
            right = x;
        } else {
            // Should not happen for a correct cycle
            // In case of error, we still proceed (but guaranteed not to occur)
        }
        used[x] = true;
    }

    // Output the guessed permutation
    cout << -1;
    for (int v : chain) cout << " " << v;
    cout << endl;
    cout.flush();

    return 0;
}