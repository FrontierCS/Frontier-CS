#include <bits/stdc++.h>
using namespace std;

int n, m;

pair<int, int> query_leave_out(int out1, int out2) {
    if (out1 > out2) swap(out1, out2);
    cout << "0 " << n - 2;
    for (int i = 1; i <= n; ++i) {
        if (i != out1 && i != out2) {
            cout << " " << i;
        }
    }
    cout << endl;
    cout.flush();
    int med1, med2;
    cin >> med1 >> med2;
    return {med1, med2};
}

int main() {
    cin >> n;
    m = n / 2;
    int fixed1 = 1;
    vector<int> pos_neither, pos_b_small, pos_a_large, pos_both, pos_amb_a, pos_amb_b;
    for (int j = 2; j <= n; ++j) {
        auto [med1, med2] = query_leave_out(fixed1, j);
        if (med1 == m && med2 == m + 1) {
            pos_neither.push_back(j);
        } else if (med1 == m && med2 == m + 2) {
            pos_b_small.push_back(j);
        } else if (med1 == m - 1 && med2 == m + 1) {
            pos_a_large.push_back(j);
        } else if (med1 == m - 1 && med2 == m + 2) {
            pos_both.push_back(j);
        } else if (med1 == m + 1 && med2 == m + 2) {
            pos_amb_a.push_back(j);
        } else if (med1 == m - 1 && med2 == m) {
            pos_amb_b.push_back(j);
        }
    }
    if (!pos_both.empty()) {
        int j = pos_both[0];
        cout << "1 " << fixed1 << " " << j << endl;
        cout.flush();
        return 0;
    }
    if (pos_b_small.size() == 1 && pos_a_large.empty()) {
        int Y = pos_b_small[0];
        sort(pos_neither.begin(), pos_neither.end());
        int L = pos_neither[0];
        vector<int> second_a_large;
        for (int j = 1; j <= n; ++j) {
            if (j == L) continue;
            auto [med1, med2] = query_leave_out(L, j);
            if (med1 == m - 1 && med2 == m + 1) {
                second_a_large.push_back(j);
            }
        }
        int X = second_a_large[0];
        cout << "1 " << X << " " << Y << endl;
        cout.flush();
        return 0;
    } else if (pos_a_large.size() == 1 && pos_b_small.empty()) {
        int X = pos_a_large[0];
        sort(pos_neither.begin(), pos_neither.end());
        int S = pos_neither[0];
        vector<int> second_b_small;
        for (int j = 1; j <= n; ++j) {
            if (j == S) continue;
            auto [med1, med2] = query_leave_out(S, j);
            if (med1 == m && med2 == m + 2) {
                second_b_small.push_back(j);
            }
        }
        int Y = second_b_small[0];
        cout << "1 " << X << " " << Y << endl;
        cout.flush();
        return 0;
    }
    // Should not reach here
    assert(false);
    return 0;
}