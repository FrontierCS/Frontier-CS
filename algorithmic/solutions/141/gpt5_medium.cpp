#include <bits/stdc++.h>
using namespace std;

int n, k;

string read_response() {
    string s;
    if (!(cin >> s)) {
        // In case of unexpected EOF, default to "N"
        s = "N";
    }
    return s;
}

bool query(int c) {
    cout << "? " << c << endl;
    cout.flush();
    string res = read_response();
    return res == "Y";
}

void reset() {
    cout << "R" << endl;
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n >> k)) {
        return 0;
    }

    vector<vector<int>> blocks;
    for (int i = 1; i <= n; i += k) {
        vector<int> b;
        for (int j = i; j <= min(n, i + k - 1); ++j) b.push_back(j);
        blocks.push_back(b);
    }

    int m = (int)blocks.size();
    vector<vector<int>> uniq(m);

    // Deduplicate within each block
    for (int i = 0; i < m; ++i) {
        reset();
        for (int idx : blocks[i]) {
            bool isDup = query(idx);
            if (!isDup) uniq[i].push_back(idx);
        }
    }

    // Remove duplicates across blocks
    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < i; ++j) {
            if (uniq[i].empty()) break;
            if (uniq[j].empty()) continue;

            reset();
            for (int x : uniq[j]) query(x);

            vector<int> kept;
            kept.reserve(uniq[i].size());
            for (int x : uniq[i]) {
                bool dup = query(x);
                if (!dup) kept.push_back(x);
            }
            uniq[i].swap(kept);
        }
    }

    int d = 0;
    for (int i = 0; i < m; ++i) d += (int)uniq[i].size();

    cout << "! " << d << endl;
    cout.flush();
    return 0;
}