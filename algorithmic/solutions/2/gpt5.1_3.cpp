#include <bits/stdc++.h>
using namespace std;

int ask(const vector<int> &a) {
    int n = (int)a.size() - 1;
    cout << "0";
    for (int i = 1; i <= n; ++i) cout << ' ' << a[i];
    cout << endl;
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
        cout << "1 1" << endl;
        cout.flush();
        return 0;
    }

    vector<int> posVal(n + 1, -1);
    vector<char> assigned_pos(n + 1, false);
    vector<int> arr(n + 1, 1);

    // Step 1: find positions of values 1 and 2
    for (int i = 1; i <= n; ++i) arr[i] = 1;
    int base = ask(arr); // should be 1

    int pos1 = -1, pos2 = -1;
    for (int i = 1; i <= n && (pos1 == -1 || pos2 == -1); ++i) {
        for (int j = 1; j <= n; ++j) arr[j] = 1;
        arr[i] = 2;
        int res = ask(arr);
        int diff = res - base;
        if (diff == -1 && pos1 == -1) pos1 = i;
        else if (diff == 1 && pos2 == -1) pos2 = i;
    }

    posVal[1] = pos1;
    posVal[2] = pos2;
    assigned_pos[pos1] = assigned_pos[pos2] = true;

    // Step 2: find positions for values 3..n using binary search
    for (int v = 3; v <= n; ++v) {
        vector<int> cand;
        cand.reserve(n);
        for (int pos = 1; pos <= n; ++pos)
            if (!assigned_pos[pos])
                cand.push_back(pos);

        while (cand.size() > 1) {
            int half = (int)cand.size() / 2;
            vector<int> T(cand.begin(), cand.begin() + half);

            // Build query
            for (int i = 1; i <= n; ++i) arr[i] = 1;
            for (int t = 1; t < v; ++t) arr[posVal[t]] = t;
            for (int idx : T) arr[idx] = v;

            int res = ask(arr); // should be (v-1) or v
            if (res == v) {
                cand = std::move(T);
            } else {
                cand.erase(cand.begin(), cand.begin() + half);
            }
        }

        int posv = cand[0];
        posVal[v] = posv;
        assigned_pos[posv] = true;
    }

    // Build final permutation q[pos] = value
    vector<int> q(n + 1);
    for (int val = 1; val <= n; ++val) {
        int pos = posVal[val];
        if (pos >= 1 && pos <= n)
            q[pos] = val;
    }

    cout << "1";
    for (int i = 1; i <= n; ++i) cout << ' ' << q[i];
    cout << endl;
    cout.flush();

    return 0;
}