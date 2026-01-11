#include <bits/stdc++.h>
using namespace std;

vector<int> longest_subseq_indices_by_keys(const vector<int> &inds, const vector<int> &keys) {
    int m = inds.size();
    if (m == 0) return {};
    vector<int> tailVal;
    vector<int> tailPos;
    vector<int> prev(m, -1);

    for (int i = 0; i < m; ++i) {
        int key = keys[i];
        int pos = lower_bound(tailVal.begin(), tailVal.end(), key) - tailVal.begin();
        if (pos == (int)tailVal.size()) {
            tailVal.push_back(key);
            tailPos.push_back(i);
        } else {
            tailVal[pos] = key;
            tailPos[pos] = i;
        }
        if (pos > 0) prev[i] = tailPos[pos - 1];
    }

    vector<int> res;
    int pos = tailPos.back();
    while (pos != -1) {
        res.push_back(inds[pos]);
        pos = prev[pos];
    }
    reverse(res.begin(), res.end());
    return res;
}

vector<int> LIS_indices(const vector<int> &inds, const vector<int> &p) {
    int m = inds.size();
    vector<int> keys(m);
    for (int i = 0; i < m; ++i) keys[i] = p[inds[i]];
    return longest_subseq_indices_by_keys(inds, keys);
}

vector<int> LDS_indices(const vector<int> &inds, const vector<int> &p) {
    int m = inds.size();
    vector<int> keys(m);
    for (int i = 0; i < m; ++i) keys[i] = -p[inds[i]];
    return longest_subseq_indices_by_keys(inds, keys);
}

int LDS_length(const vector<int> &inds, const vector<int> &p) {
    int m = inds.size();
    if (m == 0) return 0;
    vector<int> tails;
    for (int i = 0; i < m; ++i) {
        int key = -p[inds[i]];
        int pos = lower_bound(tails.begin(), tails.end(), key) - tails.begin();
        if (pos == (int)tails.size()) tails.push_back(key);
        else tails[pos] = key;
    }
    return (int)tails.size();
}

struct VariantResult {
    long long score;
    vector<char> assign; // 0:A, 1:B, 2:C, 3:D
};

VariantResult evaluate_variant(const vector<int> &perm, const vector<int> &order) {
    int n = (int)perm.size();
    vector<char> assign(n, 3); // default D
    vector<char> alive(n, 1);
    long long score = 0;

    int inc_used = 0;
    bool dec_used = false;

    for (int step = 0; step < 3; ++step) {
        vector<int> inds;
        inds.reserve(n);
        for (int i = 0; i < n; ++i) if (alive[i]) inds.push_back(i);
        if (inds.empty()) break;

        if (order[step] == 0) { // INCREASING
            vector<int> sel = LIS_indices(inds, perm);
            int gid = (inc_used == 0 ? 0 : 2); // A then C
            inc_used++;
            for (int idx : sel) {
                assign[idx] = gid;
                alive[idx] = 0;
            }
            score += (int)sel.size();
        } else { // DECREASING
            vector<int> sel = LDS_indices(inds, perm);
            int gid = 1; // B
            dec_used = true;
            for (int idx : sel) {
                assign[idx] = gid;
                alive[idx] = 0;
            }
            score += (int)sel.size();
        }
    }

    vector<int> leftover;
    leftover.reserve(n);
    for (int i = 0; i < n; ++i) if (alive[i]) leftover.push_back(i);
    score += LDS_length(leftover, perm);

    return {score, assign};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!(cin >> n)) return 0;
    vector<int> p(n);
    for (int i = 0; i < n; ++i) cin >> p[i];

    vector<vector<int>> orders = {
        {0, 0, 1}, // IN, IN, DE
        {0, 1, 0}, // IN, DE, IN
        {1, 0, 0}  // DE, IN, IN
    };

    VariantResult best{LLONG_MIN, vector<char>(n, 3)};
    for (auto &ord : orders) {
        VariantResult res = evaluate_variant(p, ord);
        if (res.score > best.score) best = std::move(res);
    }

    vector<int> a, b, c, d;
    a.reserve(n); b.reserve(n); c.reserve(n); d.reserve(n);
    for (int i = 0; i < n; ++i) {
        if (best.assign[i] == 0) a.push_back(p[i]);
        else if (best.assign[i] == 1) b.push_back(p[i]);
        else if (best.assign[i] == 2) c.push_back(p[i]);
        else d.push_back(p[i]);
    }

    cout << (int)a.size() << " " << (int)b.size() << " " << (int)c.size() << " " << (int)d.size() << "\n";
    for (int i = 0; i < (int)a.size(); ++i) {
        if (i) cout << " ";
        cout << a[i];
    }
    cout << "\n";
    for (int i = 0; i < (int)b.size(); ++i) {
        if (i) cout << " ";
        cout << b[i];
    }
    cout << "\n";
    for (int i = 0; i < (int)c.size(); ++i) {
        if (i) cout << " ";
        cout << c[i];
    }
    cout << "\n";
    for (int i = 0; i < (int)d.size(); ++i) {
        if (i) cout << " ";
        cout << d[i];
    }
    cout << "\n";
    return 0;
}