#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <set>
#include <random>
#include <ctime>

using namespace std;

int N;
int T1, T2;

pair<int, int> query(const vector<int>& idxs) {
    cout << "0 " << idxs.size();
    for (int x : idxs) cout << " " << x;
    cout << endl;
    int m1, m2;
    cin >> m1 >> m2;
    return {m1, m2};
}

void answer(int i1, int i2) {
    cout << "1 " << i1 << " " << i2 << endl;
    exit(0);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    if (!(cin >> N)) return 0;

    T1 = N / 2;
    T2 = N / 2 + 1;

    vector<int> candidates(N);
    iota(candidates.begin(), candidates.end(), 1);

    vector<int> U, D;
    vector<int> Padding;
    set<int> Known; 

    mt19937 rng(1337);

    while (candidates.size() > 2) {
        if (Known.size() == 2) {
            vector<int> res(Known.begin(), Known.end());
            answer(res[0], res[1]);
        }
        
        // Endgame for size 4
        if (candidates.size() == 4) {
            if (Padding.size() >= 2) {
                int p1 = Padding[0];
                int p2 = Padding[1];
                
                vector<int> current_c = candidates;
                for (int i = 0; i < (int)current_c.size(); ++i) {
                    for (int j = i + 1; j < (int)current_c.size(); ++j) {
                        int u = current_c[i];
                        int v = current_c[j];
                        
                        if (Known.count(u) || Known.count(v)) continue;

                        vector<int> q_idxs = {p1, p2};
                        for (int x : current_c) {
                            if (x != u && x != v) q_idxs.push_back(x);
                        }
                        
                        pair<int, int> res = query(q_idxs);
                        if (res.first == T1 && res.second == T2) {
                            vector<int> finals;
                            for(int x : current_c) if(x != u && x != v) finals.push_back(x);
                            answer(finals[0], finals[1]);
                        }
                    }
                }
            } 
            // If padding < 2, we must rely on Known or continue (should not happen for N>=6 unless found early)
            // If N=4 initially not possible per constraints (N>=6) but logic holds.
            if (Known.size() == 2) {
                 vector<int> res(Known.begin(), Known.end());
                 answer(res[0], res[1]);
            }
        }

        int u = -1, v = -1;
        bool from_lists = false;

        if (!U.empty() && !D.empty()) {
            u = U.back();
            v = D.back();
            from_lists = true;
        } else {
            vector<int> unknown;
            set<int> in_lists;
            for(int x : U) in_lists.insert(x);
            for(int x : D) in_lists.insert(x);
            for(int x : Known) in_lists.insert(x);
            
            for(int x : candidates) {
                if (!in_lists.count(x)) unknown.push_back(x);
            }

            if (unknown.size() >= 2) {
                uniform_int_distribution<int> dist(0, unknown.size() - 1);
                int idx1 = dist(rng);
                int idx2 = dist(rng);
                while (idx1 == idx2) idx2 = dist(rng);
                u = unknown[idx1];
                v = unknown[idx2];
            } else {
                if (!U.empty() && !unknown.empty()) {
                    u = U.back();
                    v = unknown[0];
                } else if (!D.empty() && !unknown.empty()) {
                    u = D.back();
                    v = unknown[0];
                } else {
                    // Fallback (unlikely)
                    if (U.size() >= 2) { u = U[U.size()-1]; v = U[U.size()-2]; }
                    else if (D.size() >= 2) { u = D[D.size()-1]; v = D[D.size()-2]; }
                }
            }
        }
        
        vector<int> q_idxs;
        for (int x : candidates) {
            if (x != u && x != v) q_idxs.push_back(x);
        }

        pair<int, int> res = query(q_idxs);

        if (res.first == T1 && res.second == T2) {
            // Success: u, v are non-medians (S, L)
            if (from_lists) {
                U.pop_back();
                D.pop_back();
            } else {
                if (!U.empty() && U.back() == u) U.pop_back();
                else if (!U.empty() && U.back() == v) U.pop_back();
                
                if (!D.empty() && D.back() == u) D.pop_back();
                else if (!D.empty() && D.back() == v) D.pop_back();
            }
            
            vector<int> next_c;
            for(int x : candidates) if(x != u && x != v) next_c.push_back(x);
            candidates = next_c;
            
            Padding.push_back(u);
            Padding.push_back(v);
        }
        else if (res.first < T1 && res.second > T2) {
            // Widen -> Found medians
            answer(u, v);
        }
        else if (res.first > T1 && res.second > T2) {
            // Shift Up
            if (!from_lists) {
                U.push_back(u);
                U.push_back(v);
            }
        }
        else if (res.first < T1 && res.second < T2) {
            // Shift Down
            if (!from_lists) {
                D.push_back(u);
                D.push_back(v);
            }
        }
        else if (res.first < T1 && res.second == T2) {
            // u=M1 case (M1, L)
            if (from_lists) {
                // u from U is M1
                Known.insert(u);
                U.pop_back();
                // v from D is L, keep in D
            }
        }
        else if (res.first == T1 && res.second > T2) {
            // v=M2 case (S, M2)
            if (from_lists) {
                // v from D is M2
                Known.insert(v);
                D.pop_back();
                // u from U is S, keep in U
            }
        }
    }

    if (candidates.size() == 2) {
        answer(candidates[0], candidates[1]);
    }

    return 0;
}