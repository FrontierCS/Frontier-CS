#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    int N = n * m;
    vector<int> f0(N);
    
    // Scan ring 0 through all positions
    for (int k = 0; k < N; ++k) {
        cout << "? 0 1" << endl;
        cin >> f0[k];
    }
    // Now ring 0 is back to initial position
    
    // Find peaks (local maxima)
    vector<int> peaks;
    for (int k = 0; k < N; ++k) {
        int prev = f0[(k - 1 + N) % N];
        int next = f0[(k + 1) % N];
        if (f0[k] > prev && f0[k] > next) {
            peaks.push_back(k);
        }
    }
    // If not enough peaks, take the highest f0 values
    if ((int)peaks.size() < n - 1) {
        vector<pair<int, int>> v;
        for (int k = 0; k < N; ++k) v.emplace_back(f0[k], k);
        sort(v.rbegin(), v.rend());
        set<int> taken;
        for (auto &[val, pos] : v) {
            if ((int)taken.size() >= n - 1) break;
            taken.insert(pos);
        }
        peaks.assign(taken.begin(), taken.end());
    }
    // If too many peaks, keep only the highest n-1
    if ((int)peaks.size() > n - 1) {
        sort(peaks.begin(), peaks.end(), [&](int a, int b) { return f0[a] > f0[b]; });
        peaks.resize(n - 1);
    }
    sort(peaks.begin(), peaks.end());
    int M = peaks.size();
    
    // delta[peak_idx][ring] = change when rotating that ring at that peak
    vector<vector<int>> delta(M, vector<int>(n, 0));
    int current_offset = 0; // current rotation of ring 0 from initial
    
    for (int idx = 0; idx < M; ++idx) {
        int p = peaks[idx];
        // Move ring 0 to position p
        int diff = (p - current_offset + N) % N;
        if (diff <= N / 2) {
            for (int r = 0; r < diff; ++r) {
                cout << "? 0 1" << endl;
                int tmp; cin >> tmp;
            }
        } else {
            int steps = N - diff;
            for (int r = 0; r < steps; ++r) {
                cout << "? 0 -1" << endl;
                int tmp; cin >> tmp;
            }
        }
        current_offset = p;
        
        // For each ring i (1..n-1), measure delta
        for (int i = 1; i < n; ++i) {
            cout << "? " << i << " 1" << endl;
            int f1; cin >> f1;
            cout << "? " << i << " -1" << endl;
            int f2; cin >> f2;
            delta[idx][i] = f1 - f2; // change when rotating i forward then back
        }
    }
    
    // Greedy assignment: for each ring i, pick the unassigned peak with largest |delta|
    vector<int> assigned_peak(n, -1);
    vector<bool> peak_used(M, false);
    for (int i = 1; i < n; ++i) {
        int best_idx = -1;
        int best_val = -1;
        for (int idx = 0; idx < M; ++idx) {
            if (peak_used[idx]) continue;
            int abs_delta = abs(delta[idx][i]);
            if (abs_delta > best_val) {
                best_val = abs_delta;
                best_idx = idx;
            }
        }
        assigned_peak[i] = peaks[best_idx];
        peak_used[best_idx] = true;
    }
    
    // Output answer
    cout << "!";
    for (int i = 1; i < n; ++i) {
        cout << " " << assigned_peak[i];
    }
    cout << endl;
    
    return 0;
}