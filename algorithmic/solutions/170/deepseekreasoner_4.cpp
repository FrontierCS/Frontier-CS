#include <bits/stdc++.h>
using namespace std;

const int N = 100;
const long long L = 500000;
const int TRIAL = 50; // number of trials

struct Result {
    long long error;
    vector<int> a, b;
};

// run one greedy trial with random tie-breaking
Result run_trial(const vector<int>& T, mt19937& rng) {
    vector<int> count(N, 0);
    vector<int> a(N, -1), b(N, -1);
    
    count[0] = 1;
    int current = 0;
    
    for (long long week = 2; week <= L; ++week) {
        int x = current;
        int t = count[x];
        if (t % 2 == 1) { // odd
            if (a[x] == -1) {
                // find max deficit
                int max_deficit = -1e9;
                for (int i = 0; i < N; ++i) {
                    int deficit = T[i] - count[i];
                    if (deficit > max_deficit) max_deficit = deficit;
                }
                // collect candidates with max deficit
                vector<int> cand;
                for (int i = 0; i < N; ++i) {
                    if (T[i] - count[i] == max_deficit) cand.push_back(i);
                }
                // random choice
                uniform_int_distribution<int> dist(0, cand.size() - 1);
                a[x] = cand[dist(rng)];
            }
            current = a[x];
        } else { // even
            if (b[x] == -1) {
                int max_deficit = -1e9;
                for (int i = 0; i < N; ++i) {
                    int deficit = T[i] - count[i];
                    if (deficit > max_deficit) max_deficit = deficit;
                }
                vector<int> cand;
                for (int i = 0; i < N; ++i) {
                    if (T[i] - count[i] == max_deficit) cand.push_back(i);
                }
                uniform_int_distribution<int> dist(0, cand.size() - 1);
                b[x] = cand[dist(rng)];
            }
            current = b[x];
        }
        count[current]++;
    }
    
    // set unset a,b to 0
    for (int i = 0; i < N; ++i) {
        if (a[i] == -1) a[i] = 0;
        if (b[i] == -1) b[i] = 0;
    }
    
    // compute error
    long long error = 0;
    for (int i = 0; i < N; ++i) {
        error += abs(count[i] - T[i]);
    }
    
    return {error, a, b};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    long long l;
    cin >> n >> l; // n is always 100, l always 500000
    vector<int> T(N);
    for (int i = 0; i < N; ++i) {
        cin >> T[i];
    }
    
    random_device rd;
    mt19937 rng(rd());
    
    Result best;
    best.error = 1e18;
    
    for (int trial = 0; trial < TRIAL; ++trial) {
        Result res = run_trial(T, rng);
        if (res.error < best.error) {
            best = move(res);
        }
    }
    
    // output
    for (int i = 0; i < N; ++i) {
        cout << best.a[i] << " " << best.b[i] << "\n";
    }
    
    return 0;
}