#include <bits/stdc++.h>
using namespace std;

int n;
vector<int> perm;

void output_query(const vector<int>& qq) {
    cout << 0;
    for (int j = 1; j <= n; ++j) {
        cout << " " << qq[j];
    }
    cout << endl;
    cout.flush();
}

int read_response() {
    int x;
    cin >> x;
    return x;
}

void solve(const vector<int>& positions, const vector<int>& values,
           const vector<pair<vector<int>, int>>& externals) {
    int m = positions.size();
    if (m == 0) return;
    if (m == 1) {
        perm[positions[0]] = values[0];
        return;
    }
    int half = m / 2;
    vector<int> left_pos(positions.begin(), positions.begin() + half);
    vector<int> right_pos(positions.begin() + half, positions.end());
    int uu = values[0];
    vector<int> xx(m);
    for (int i = 0; i < m; ++i) {
        int w = values[i];
        vector<int> qq(n + 1, 0);
        // set known
        for (int j = 1; j <= n; ++j) {
            if (perm[j] != 0) {
                qq[j] = perm[j];
            }
        }
        // set current left to w
        for (int j : left_pos) {
            qq[j] = w;
        }
        // set current right_sub to uu
        for (int j : right_pos) {
            qq[j] = uu;
        }
        // set externals
        for (const auto& ex : externals) {
            for (int j : ex.first) {
                qq[j] = ex.second;
            }
        }
        output_query(qq);
        xx[i] = read_response();
    }
    // determine left_vals
    int minx = *min_element(xx.begin(), xx.end());
    vector<int> leftv;
    for (int i = 0; i < m; ++i) {
        if (xx[i] == minx + 1) {
            leftv.push_back(values[i]);
        }
    }
    if ((int)leftv.size() != (int)left_pos.size()) {
        // fallback, perhaps all same, but shouldn't happen
        leftv.clear();
        for (int i = 0; i < m; ++i) {
            if (xx[i] == maxx) {  // try max
                leftv.push_back(values[i]);
            }
        }
    }
    vector<int> rightv;
    set<int> left_set(leftv.begin(), leftv.end());
    for (int vv : values) {
        if (left_set.find(vv) == left_set.end()) {
            rightv.push_back(vv);
        }
    }
    // recurse left
    vector<pair<vector<int>, int>> ext_left = externals;
    if (!rightv.empty()) {
        ext_left.emplace_back(right_pos, rightv[0]);
    }
    solve(left_pos, leftv, ext_left);
    // recurse right
    vector<pair<vector<int>, int>> ext_right = externals;
    solve(right_pos, rightv, ext_right);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    cin >> n;
    perm.assign(n + 1, 0);
    vector<int> poss(n);
    for (int i = 0; i < n; ++i) poss[i] = i + 1;
    vector<int> vals(n);
    for (int i = 0; i < n; ++i) vals[i] = i + 1;
    vector<pair<vector<int>, int>> empty_ext;
    solve(poss, vals, empty_ext);
    // now output the guess
    cout << 1;
    for (int j = 1; j <= n; ++j) {
        cout << " " << perm[j];
    }
    cout << endl;
    cout.flush();
    return 0;
}