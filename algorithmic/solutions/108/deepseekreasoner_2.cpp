#include <bits/stdc++.h>
using namespace std;

int n, m, N;
vector<int> a0; // a[t] for t=0..N-1 from initial scan
vector<int> peaks; // list of peak positions t
vector<int> orig_peak_a; // a0 at peaks

// Helper to rotate ring0 from current position cur to target t,
// performing queries, updating cur, and returning the final a value.
int rotate_to(int target, int &cur, bool read_only = true) {
    int diff = (target - cur + N) % N;
    int val = 0;
    if (diff <= N / 2) {
        for (int k = 0; k < diff; ++k) {
            cout << "? 0 1" << endl;
            cin >> val;
        }
    } else {
        int adiff = N - diff;
        for (int k = 0; k < adiff; ++k) {
            cout << "? 0 -1" << endl;
            cin >> val;
        }
    }
    cur = target;
    return val;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> n >> m;
    N = n * m;
    a0.resize(N);

    // Step 1: initial scan of ring0
    int val;
    for (int t = 1; t <= N; ++t) {
        cout << "? 0 1" << endl;
        cin >> val;
        if (t < N) {
            a0[t] = val;
        } else {
            a0[0] = val; // after N rotations we are back to start
        }
    }
    // ring0 is now at original position (cur0 = 0)

    // Step 2: find peaks (local maxima)
    for (int t = 0; t < N; ++t) {
        int prev = a0[(t - 1 + N) % N];
        int next = a0[(t + 1) % N];
        if (a0[t] > prev && a0[t] > next) {
            peaks.push_back(t);
        }
    }

    // In case there are more peaks than n-1, we keep only the strongest n-1 peaks.
    // But we assume the number of peaks is at least n-1.
    // If there are fewer,