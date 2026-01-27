#include <bits/stdc++.h>
using namespace std;

static mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

int ask(const vector<int>& q) {
    cout << 0;
    for (int x : q) {
        cout << ' ' << x;
    }
    cout << '\n';
    cout.flush();
    int x;
    if (!(cin >> x)) exit(0);
    if (x < 0) exit(0);
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    if (n == 1) {
        cout << "1 1\n";
        cout.flush();
        return 0;
    }

    uniform_int_distribution<int> dist(1, n);

    vector<int> base(n);
    int baseAns = -1;

    // Find a base query with zero matches
    while (true) {
        for (int i = 0; i < n; ++i) base[i] = dist(rng);
        baseAns = ask(base);
        if (baseAns == 0) break;
    }

    vector<int> remaining_positions(n);
    iota(remaining_positions.begin(), remaining_positions.end(), 0);
    vector<int> pos_of_value(n + 1, -1);

    vector<int> temp(n);

    for (int v = 1; v <= n; ++v) {
        if ((int)remaining_positions.size() == 1) {
            pos_of_value[v] = remaining_positions[0];
            remaining_positions.pop_back();
            break;
        }

        vector<int> candidates = remaining_positions;

        while ((int)candidates.size() > 1) {
            int m = (int)candidates.size();
            int half = m / 2;

            vector<int> left(candidates.begin(), candidates.begin() + half);
            vector<int> right(candidates.begin() + half, candidates.end());

            temp = base;
            for (int idx : left) temp[idx] = v;

            int res = ask(temp); // since base has 0 matches, res is 1 if pos(v) in left, else 0
            if (res == 1) {
                candidates.swap(left);
            } else {
                candidates.swap(right);
            }
        }

        int pos = candidates[0];
        pos_of_value[v] = pos;

        // remove pos from remaining_positions
        auto it = find(remaining_positions.begin(), remaining_positions.end(), pos);
        if (it != remaining_positions.end()) remaining_positions.erase(it);
    }

    // If some values remain (only possible when n>=2), assign last by leftover positions
    while (!remaining_positions.empty()) {
        int pos = remaining_positions.back();
        remaining_positions.pop_back();
        // find an unassigned value
        int v = -1;
        for (int val = 1; val <= n; ++val) {
            if (pos_of_value[val] == -1) { v = val; break; }
        }
        if (v != -1) pos_of_value[v] = pos;
    }

    vector<int> perm(n, 0);
    for (int v = 1; v <= n; ++v) {
        if (pos_of_value[v] != -1) perm[pos_of_value[v]] = v;
    }

    cout << 1;
    for (int i = 0; i < n; ++i) cout << ' ' << perm[i];
    cout << '\n';
    cout.flush();

    return 0;
}