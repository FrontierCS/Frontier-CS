#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

int query(const string& s) {
    cout << "? " << s << endl;
    int res;
    cin >> res;
    return res;
}

void solve() {
    int n;
    cin >> n;
    if (n == 1) {
        cout << "! 1" << endl;
        return;
    }
    vector<bool> inS(n, false);
    // start with vertex 0
    inS[0] = true;
    int sizeS = 1;
    // initial query for S = {0}
    string s(n, '0');
    s[0] = '1';
    int qS = query(s);
    if (qS == 0) {
        // isolated vertex, disconnected
        cout << "! 0" << endl;
        return;
    }
    while (sizeS < n) {
        // build current S string
        s.assign(n, '0');
        for (int i = 0; i < n; ++i) {
            if (inS[i]) s[i] = '1';
        }
        qS = query(s);
        if (qS == 0) {
            // no neighbors outside S, but |S| < n => disconnected
            cout << "! 0" << endl;
            return;
        }
        // build list of vertices not in S
        vector<int> U;
        for (int i = 0; i < n; ++i) {
            if (!inS[i]) U.push_back(i);
        }
        int m = U.size();
        if (m == 1) {
            // only one vertex outside S, and qS > 0 => it must be adjacent
            inS[U[0]] = true;
            sizeS++;
            if (sizeS == n) {
                cout << "! 1" << endl;
                return;
            }
            continue;
        }
        // binary search on U to find a vertex adjacent to S
        int low = 0, high = m - 1;
        while (low < high) {
            int mid = (low + high) / 2;
            // T = U[low..mid]
            string t_str(n, '0');
            for (int i = low; i <= mid; ++i) {
                t_str[U[i]] = '1';
            }
            int qT = query(t_str);
            // S union T
            string st_str = s;
            for (int i = low; i <= mid; ++i) {
                st_str[U[i]] = '1';
            }
            int qST = query(st_str);
            if (qS + qT > qST) {
                // there is a vertex in T adjacent to S
                high = mid;
            } else {
                low = mid + 1;
            }
        }
        // U[low] is adjacent to S
        inS[U[low]] = true;
        sizeS++;
        if (sizeS == n) {
            cout << "! 1" << endl;
            return;
        }
    }
    // should not reach here
    cout << "! 1" << endl;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int T;
    cin >> T;
    while (T--) {
        solve();
    }
    return 0;
}