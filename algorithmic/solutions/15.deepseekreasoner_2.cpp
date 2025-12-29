#include <bits/stdc++.h>
using namespace std;

using Perm = vector<int>;

struct Op {
    int x, y;
};

Perm apply_operation(const Perm& p, int x, int y) {
    int n = p.size();
    Perm res;
    // suffix of length y
    for (int i = n - y; i < n; ++i) res.push_back(p[i]);
    // middle of length n - x - y
    for (int i = x; i < n - y; ++i) res.push_back(p[i]);
    // prefix of length x
    for (int i = 0; i < x; ++i) res.push_back(p[i]);
    return res;
}

vector<Op> bfs_sort(const Perm& start, Perm& target) {
    int n = start.size();
    map<Perm, pair<Perm, Op>> prev;
    queue<Perm> q;
    q.push(start);
    prev[start] = {start, {-1, -1}}; // dummy op

    while (!q.empty()) {
        Perm cur = q.front(); q.pop();
        // generate all operations
        for (int x = 1; x <= n-2; ++x) {
            for (int y = 1; x + y < n; ++y) {
                Perm nxt = apply_operation(cur, x, y);
                if (prev.find(nxt) == prev.end()) {
                    prev[nxt] = {cur, {x, y}};
                    q.push(nxt);
                }
            }
        }
    }

    // find lexicographically smallest permutation among reachable
    target = start;
    for (const auto& entry : prev) {
        if (entry.first < target) {
            target = entry.first;
        }
    }

    // reconstruct path from start to target
    vector<Op> ops;
    Perm cur = target;
    while (cur != start) {
        auto [pr, op] = prev[cur];
        ops.push_back(op);
        cur = pr;
    }
    reverse(ops.begin(), ops.end());
    return ops;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int n;
    cin >> n;
    Perm p(n);
    for (int i = 0; i < n; ++i) cin >> p[i];

    vector<Op> operations;

    if (n <= 8) {
        Perm target;
        operations = bfs_sort(p, target);
        // target is lexicographically smallest reachable
        // operations already computed
    } else {
        // For n > 8, we assume sorted permutation is reachable and use a simple heuristic.
        // We try to sort by repeatedly bringing the smallest element to front and then moving it to back.
        // This may not always work, but it's a heuristic.
        Perm cur = p;
        // We'll limit the number of operations to 4n.
        int limit = 4 * n;
        while (limit > 0) {
            // Check if sorted
            bool sorted = true;
            for (int i = 0; i < n; ++i) {
                if (cur[i] != i+1) {
                    sorted = false;
                    break;
                }
            }
            if (sorted) break;

            // Find smallest element and its position
            int min_pos = 0;
            for (int i = 1; i < n; ++i) {
                if (cur[i] < cur[min_pos]) min_pos = i;
            }

            if (min_pos == 0) {
                // smallest is already at front, move it to back
                operations.push_back({1, 1});
                cur = apply_operation(cur, 1, 1);
                limit--;
            } else if (min_pos > 1) {
                // bring to front in one operation
                int y = n - min_pos;
                operations.push_back({1, y});
                cur = apply_operation(cur, 1, y);
                limit--;
                // then move to back
                operations.push_back({1, 1});
                cur = apply_operation(cur, 1, 1);
                limit--;
            } else { // min_pos == 1
                // move to end first
                operations.push_back({2, 1});
                cur = apply_operation(cur, 2, 1);
                limit--;
                // then bring to front
                operations.push_back({1, 1});
                cur = apply_operation(cur, 1, 1);
                limit--;
                // then move to back
                operations.push_back({1, 1});
                cur = apply_operation(cur, 1, 1);
                limit--;
            }
        }
        // If after loop still not sorted, we clear operations and output empty (fallback)
        bool sorted = true;
        for (int i = 0; i < n; ++i) {
            if (cur[i] != i+1) {
                sorted = false;
                break;
            }
        }
        if (!sorted) {
            operations.clear(); // fallback to no operations
        }
    }

    cout << operations.size() << '\n';
    for (const auto& op : operations) {
        cout << op.x << ' ' << op.y << '\n';
    }

    return 0;
}