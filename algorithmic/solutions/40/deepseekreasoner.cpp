#include <bits/stdc++.h>
using namespace std;

int n;

int query(const vector<int>& indices) {
    int k = indices.size();
    cout << "0 " << k;
    for (int idx : indices) cout << ' ' << idx;
    cout << endl;
    cout.flush();
    int res;
    cin >> res;
    return res;
}

// Find an index in range [l, r] that is '(' using known close index
int find_open(int l, int r, int known_close) {
    if (l == r) return l;
    int mid = (l + r) / 2;
    vector<int> A;
    for (int i = l; i <= mid; ++i) A.push_back(i);
    vector<int> qry = A;
    qry.push_back(known_close);
    int f = query(qry);
    if (f > 0) {
        return find_open(l, mid, known_close);
    } else {
        return find_open(mid+1, r, known_close);
    }
}

// Find an index in range [l, r] that is ')' using known open index
int find_close(int l, int r, int known_open) {
    if (l == r) return l;
    int mid = (l + r) / 2;
    vector<int> A;
    for (int i = l; i <= mid; ++i) A.push_back(i);
    vector<int> qry;
    qry.push_back(known_open);
    for (int x : A) qry.push_back(x);
    int f = query(qry);
    if (f > 0) {
        return find_close(l, mid, known_open);
    } else {
        return find_close(mid+1, r, known_open);
    }
}

// Find any pair (open, close) with s[open]='(', s[close]=')'
pair<int,int> find_pair(int l, int r) {
    if (l == r) return {-1, -1}; // shouldn't happen
    int mid = (l + r) / 2;
    // Build A and B
    vector<int> A, B;
    for (int i = l; i <= mid; ++i) A.push_back(i);
    for (int i = mid+1; i <= r; ++i) B.push_back(i);
    // Query A then B
    vector<int> qry1 = A;
    qry1.insert(qry1.end(), B.begin(), B.end());
    int f1 = query(qry1);
    if (f1 > 0) {
        // '(' in A, ')' in B
        // First find a ')' in B using any from A? We need an opening to find a closing.
        // Instead, first find an opening in A using B's known existence of ')'.
        // We can pick any index from B as a candidate close? But we need a known close.
        // We can use binary search on A to find an opening, using the whole B as a probe.
        int open = find_open(l, mid, B[0]); // using B[0] as provisional close
        // Now find a close in B using the found open
        int close = find_close(mid+1, r, open);
        return {open, close};
    }
    // Query B then A
    vector<int> qry2 = B;
    qry2.insert(qry2.end(), A.begin(), A.end());
    int f2 = query(qry2);
    if (f2 > 0) {
        // '(' in B, ')' in A
        int open = find_open(mid+1, r, A[0]);
        int close = find_close(l, mid, open);
        return {open, close};
    }
    // Both zero => one half all '(', the other all ')'
    // Test first of A and first of B with alternating pattern
    int a = A[0], b = B[0];
    vector<int> qry3 = {a, b, a, b};
    int f3 = query(qry3);
    if (f3 > 0) {
        return {a, b};
    } else {
        return {b, a};
    }
}

int main() {
    cin >> n;
    // Find a pair (open, close)
    pair<int,int> p = find_pair(1, n);
    int open_idx = p.first, close_idx = p.second;
    // Now determine the rest
    string ans(n+1, '?');
    ans[open_idx] = '(';
    ans[close_idx] = ')';
    for (int i = 1; i <= n; ++i) {
        if (i == open_idx || i == close_idx) continue;
        vector<int> qry = {open_idx, open_idx, i, close_idx};
        int f = query(qry);
        if (f == 1) ans[i] = '(';
        else if (f == 2) ans[i] = ')';
        else {
            // Unexpected, but according to analysis it should be 1 or 2.
            // In case of error, guess.
            ans[i] = '(';
        }
    }
    cout << "1 ";
    for (int i = 1; i <= n; ++i) cout << ans[i];
    cout << endl;
    cout.flush();
    return 0;
}