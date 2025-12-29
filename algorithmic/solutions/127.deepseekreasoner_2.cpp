#include <bits/stdc++.h>
using namespace std;

int n;

pair<int, int> query(int i) {
    cout << "? " << i << endl;
    int a0, a1;
    cin >> a0 >> a1;
    return {a0, a1};
}

void answer(int i) {
    cout << "! " << i << endl;
    exit(0);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> n;

    int T = -1;                // maximum s seen
    int p = -1;                // index with that s
    int a0_p = 0, a1_p = 0;    // answer for p

    // sample the first min(50, n) indices
    int sample = min(50, n);
    for (int i = 0; i < sample; ++i) {
        auto [a0, a1] = query(i);
        int s = a0 + a1;
        if (s == 0) {
            answer(i);
        }
        if (s > T) {
            T = s;
            p = i;
            a0_p = a0;
            a1_p = a1;
        }
    }

    // total number of boxes with s < T
    int E = a0_p + a1_p;
    int left_count = a0_p;
    int right_count = a1_p;
    int count_found = 0;   // number of expensive boxes found so far

    // lambda to find the leftmost expensive box in [lo, hi]
    auto find_next_expensive = [&](int lo, int hi, int T, int& count_found) -> int {
        while (lo < hi) {
            int mid = (lo + hi) / 2;
            auto [a0, a1] = query(mid);
            int s = a0 + a1;
            if (s == 0) answer(mid);
            if (s < T) {        // expensive
                hi = mid;
            } else {            // cheap (s >= T)
                if (a0 > count_found) {
                    hi = mid - 1;
                } else {
                    lo = mid + 1;
                }
            }
        }
        // lo == hi
        auto [a0, a1] = query(lo);
        int s = a0 + a1;
        if (