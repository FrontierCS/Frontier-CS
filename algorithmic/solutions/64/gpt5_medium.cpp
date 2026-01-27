#include <bits/stdc++.h>
using namespace std;

static inline long long absll(long long x){ return x >= 0 ? x : -x; }

struct Solution {
    vector<unsigned char> pick;
    long long sum;
    long long diff;
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    long long T;
    if(!(cin >> n >> T)) return 0;
    vector<long long> a(n);
    for(int i=0;i<n;i++) cin >> a[i];
    long long S = 0;
    for(long long v : a) S += v;

    auto start_time = chrono::steady_clock::now();
    auto elapsed = [&](){
        return chrono::duration<double>(chrono::steady_clock::now() - start_time).count();
    };
    const double TIME_LIMIT = 0.95; // seconds

    std::mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

    auto make_solution = [&](const vector<int>& order, bool start_full, bool steepest)->Solution{
        vector<unsigned char> pick(n, 0);
        long long sum = 0;
        if(start_full){
            for(int i=0;i<n;i++){ pick[i] = 1; }
            sum = S;
        }
        if(steepest){
            if(!start_full){
                // Steepest-add: start empty, add best-improving items greedily
                bool improved = true;
                while(improved){
                    improved = false;
                    long long best_diff = absll(sum - T);
                    int best_i = -1;
                    for(int i=0;i<n;i++){
                        if(pick[i]) continue;
                        long long ns = sum + a[i];
                        long long d = absll(ns - T);
                        if(d < best_diff){
                            best_diff = d;
                            best_i = i;
                        }
                    }
                    if(best_i != -1){
                        pick[best_i] = 1;
                        sum += a[best_i];
                        improved = true;
                    }
                }
            } else {
                // Steepest-remove: start full, remove best-improving items greedily
                bool improved = true;
                while(improved){
                    improved = false;
                    long long best_diff = absll(sum - T);
                    int best_i = -1;
                    for(int i=0;i<n;i++){
                        if(!pick[i]) continue;
                        long long ns = sum - a[i];
                        long long d = absll(ns - T);
                        if(d < best_diff){
                            best_diff = d;
                            best_i = i;
                        }
                    }
                    if(best_i != -1){
                        pick[best_i] = 0;
                        sum -= a[best_i];
                        improved = true;
                    }
                }
            }
        } else {
            if(!start_full){
                long long best_diff = absll(sum - T);
                for(int idx: order){
                    long long ns = sum + a[idx];
                    long long d = absll(ns - T);
                    if(d <= best_diff){
                        best_diff = d;
                        pick[idx] = 1;
                        sum = ns;
                    }
                }
            } else {
                long long best_diff = absll(sum - T);
                for(int idx: order){
                    long long ns = sum - a[idx];
                    long long d = absll(ns - T);
                    if(d <= best_diff){
                        best_diff = d;
                        pick[idx] = 0;
                        sum = ns;
                    }
                }
            }
        }
        Solution sol;
        sol.pick = move(pick);
        sol.sum = sum;
        sol.diff = absll(sum - T);
        return sol;
    };

    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);

    vector<Solution> candidates;

    // Greedy descending
    {
        auto ord = idx;
        sort(ord.begin(), ord.end(), [&](int i, int j){ return a[i] > a[j]; });
        candidates.push_back(make_solution(ord, false, false));
        candidates.push_back(make_solution(ord, true, false));
    }

    // Greedy ascending
    {
        auto ord = idx;
        sort(ord.begin(), ord.end(), [&](int i, int j){ return a[i] < a[j]; });
        candidates.push_back(make_solution(ord, false, false));
        candidates.push_back(make_solution(ord, true, false));
    }

    // Steepest add/remove
    candidates.push_back(make_solution(idx, false, true));
    candidates.push_back(make_solution(idx, true, true));

    // Randomized greedy orders
    int R = 80;
    for(int r=0; r<R && elapsed() < TIME_LIMIT * 0.5; r++){
        vector<pair<long double,int>> w(n);
        for(int i=0;i<n;i++){
            long double rv = (long double)(rng() & ((1ULL<<53)-1)) / (long double)((1ULL<<53)-1);
            // random weight to perturb order, bias slightly by size
            w[i] = make_pair((long double)a[i] * (0.8L + 0.4L*rv), i);
        }
        sort(w.begin(), w.end(), [&](auto &x, auto &y){ return x.first > y.first; });
        vector<int> ord(n);
        for(int i=0;i<n;i++) ord[i] = w[i].second;
        candidates.push_back(make_solution(ord, false, false));
    }

    // Select top K candidates
    for(auto &c : candidates) c.diff = absll(c.sum - T);
    sort(candidates.begin(), candidates.end(), [&](const Solution& A, const Solution& B){
        if(A.diff != B.diff) return A.diff < B.diff;
        return A.sum < B.sum;
    });

    if(!candidates.empty() && candidates[0].diff == 0){
        for(int i=0;i<n;i++) cout << int(candidates[0].pick[i]);
        cout << '\n';
        return 0;
    }

    int K = min<int>(5, candidates.size());

    auto local_improve = [&](Solution &sol){
        vector<unsigned char> &pick = sol.pick;
        long long &sum = sol.sum;
        long long curr_diff = absll(sum - T);
        int N = n;
        // First perform 1-flip improvements until none
        while(elapsed() < TIME_LIMIT){
            long long best_improve = 0;
            int best_i = -1;
            long long best_new_sum = sum;
            long long best_new_diff = curr_diff;
            for(int i=0;i<N;i++){
                long long ns = sum + (pick[i] ? -a[i] : a[i]);
                long long nd = absll(ns - T);
                long long imp = curr_diff - nd;
                if(imp > best_improve){
                    best_improve = imp;
                    best_i = i;
                    best_new_sum = ns;
                    best_new_diff = nd;
                }
            }
            if(best_i == -1) break;
            pick[best_i] ^= 1;
            sum = best_new_sum;
            curr_diff = best_new_diff;
            if(curr_diff == 0) break;
        }
        // Then attempt 2-flip improvements iteratively
        bool improved_any = true;
        while(improved_any && elapsed() < TIME_LIMIT){
            improved_any = false;
            long long best_improve = 0;
            int bi = -1, bj = -1;
            long long best_new_sum = sum;
            long long best_new_diff = curr_diff;
            // Precompute deltas for 1 toggle
            vector<long long> d1(N);
            for(int i=0;i<N;i++){
                d1[i] = pick[i] ? -a[i] : a[i];
            }
            for(int i=0;i<N && elapsed() < TIME_LIMIT;i++){
                long long di = d1[i];
                for(int j=i+1;j<N;j++){
                    long long ns = sum + di + d1[j];
                    long long nd = absll(ns - T);
                    long long imp = curr_diff - nd;
                    if(imp > best_improve){
                        best_improve = imp;
                        bi = i; bj = j;
                        best_new_sum = ns;
                        best_new_diff = nd;
                    }
                }
            }
            if(bi != -1){
                pick[bi] ^= 1;
                pick[bj] ^= 1;
                sum = best_new_sum;
                curr_diff = best_new_diff;
                improved_any = true;
                if(curr_diff == 0) break;
                // after a pair improvement, try some 1-flip quick pass
                while(elapsed() < TIME_LIMIT){
                    long long best_imp1 = 0;
                    int best_i = -1;
                    long long bsum = sum, bdiff = curr_diff;
                    for(int i=0;i<N;i++){
                        long long ns = sum + (pick[i] ? -a[i] : a[i]);
                        long long nd = absll(ns - T);
                        long long imp = curr_diff - nd;
                        if(imp > best_imp1){
                            best_imp1 = imp;
                            best_i = i;
                            bsum = ns;
                            bdiff = nd;
                        }
                    }
                    if(best_i == -1) break;
                    pick[best_i] ^= 1;
                    sum = bsum;
                    curr_diff = bdiff;
                    if(curr_diff == 0) break;
                }
            }
        }
        sol.sum = sum;
        sol.diff = curr_diff;
    };

    Solution best = candidates.empty() ? Solution{vector<unsigned char>(n, 0), 0, absll(T)} : candidates[0];

    for(int i=0;i<K && elapsed() < TIME_LIMIT; i++){
        Solution cur = candidates[i];
        local_improve(cur);
        if(cur.diff < best.diff){
            best = cur;
            if(best.diff == 0) break;
        }
    }

    // If time remains, do a few random perturbations from best and improve
    while(elapsed() < TIME_LIMIT * 0.98){
        Solution cur = best;
        // random small perturbation
        int flips = 3 + (rng() % 5); // 3..7 flips
        for(int f=0; f<flips; f++){
            int i = rng() % n;
            cur.pick[i] ^= 1;
            cur.sum += cur.pick[i] ? a[i] : -a[i];
        }
        cur.diff = absll(cur.sum - T);
        local_improve(cur);
        if(cur.diff < best.diff){
            best = cur;
            if(best.diff == 0) break;
        } else {
            // try another
        }
    }

    for(int i=0;i<n;i++) cout << int(best.pick[i]);
    cout << '\n';
    return 0;
}