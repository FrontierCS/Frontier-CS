#include <bits/stdc++.h>
using namespace std;

pair<int, int> is_mixed_query(int l, int r) {
    // Dummy return, not used
    return {0, 0};
}

bool is_mixed(int l, int r) {
    int len = r - l + 1;
    if (len <= 1) return false;
    if (len <= 500) {
        vector<int> seq;
        for (int rep = 0; rep < 2; ++rep) {
            for (int j = l; j <= r; ++j) {
                seq.push_back(j);
            }
        }
        int kk = seq.size();
        cout << "0 " << kk;
        for (int x : seq) cout << " " << x;
        cout << endl;
        cout.flush();
        int ff;
        cin >> ff;
        return ff > 0;
    } else {
        int mid = (l + r) / 2;
        bool left = is_mixed(l, mid);
        if (left) return true;
        bool rightt = is_mixed(mid + 1, r);
        if (rightt) return true;
        // both uniform, check boundary
        int p1 = mid, p2 = mid + 1;
        cout << "0 2 " << p1 << " " << p2 << endl;
        cout.flush();
        int a;
        cin >> a;
        cout << "0 2 " << p2 << " " << p1 << endl;
        cout.flush();
        int b;
        cin >> b;
        return (a == 1 || b == 1);
    }
}

pair<int, int> find_pair(int l, int r) {
    int len = r - l + 1;
    if (len <= 2) {
        if (len == 1) {
            // Should not happen
            assert(false);
            return {l, l};
        }
        int p1 = l, p2 = r;
        cout << "0 2 " << p1 << " " << p2 << endl;
        cout.flush();
        int a;
        cin >> a;
        cout << "0 2 " << p2 << " " << p1 << endl;
        cout.flush();
        int b;
        cin >> b;
        if (a == 1 && b == 0) {
            return {p1, p2};
        } else {
            return {p2, p1};
        }
    }
    int mid = (l + r) / 2;
    bool mleft = is_mixed(l, mid);
    if (mleft) {
        return find_pair(l, mid);
    }
    bool mright = is_mixed(mid + 1, r);
    if (mright) {
        return find_pair(mid + 1, r);
    }
    // both uniform, different types
    int p1 = mid, p2 = mid + 1;
    cout << "0 2 " << p1 << " " << p2 << endl;
    cout.flush();
    int a;
    cin >> a;
    cout << "0 2 " << p2 << " " << p1 << endl;
    cout.flush();
    int b;
    cin >> b;
    if (a == 1 && b == 0) {
        return {p1, p2};
    } else {
        return {p2, p1};
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n;
    cin >> n;
    auto [open_pos, close_pos] = find_pair(1, n);
    string ss(n + 1, ' ');
    ss[open_pos] = '(';
    ss[close_pos] = ')';
    vector<int> unknowns;
    for (int i = 1; i <= n; ++i) {
        if (i != open_pos && i != close_pos) {
            unknowns.push_back(i);
        }
    }
    int m = unknowns.size();
    int group_size = 8;
    int num_groups = (m + group_size - 1) / group_size;
    for (int g = 0; g < num_groups; ++g) {
        int start = g * group_size;
        int end = min(start + group_size, m);
        int gs = end - start;
        vector<int> seq;
        for (int ii = 0; ii < gs; ++ii) {
            int idx = unknowns[start + ii];
            int rep = 1 << ii;
            for (int rr = 0; rr < rep; ++rr) {
                seq.push_back(idx);
                seq.push_back(close_pos);
                seq.push_back(close_pos);
            }
        }
        int kk = seq.size();
        cout << "0 " << kk;
        for (int x : seq) {
            cout << " " << x;
        }
        cout << endl;
        cout.flush();
        int ff;
        cin >> ff;
        for (int ii = 0; ii < gs; ++ii) {
            bool is_open = (ff & (1 << ii)) != 0;
            int pos = unknowns[start + ii];
            ss[pos] = is_open ? '(' : ')';
        }
    }
    cout << "1";
    for (int i = 1; i <= n; ++i) {
        cout << ss[i];
    }
    cout << endl;
    cout.flush();
    return 0;
}