#include <bits/stdc++.h>
using namespace std;

mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

bool ask(const vector<int>& S) {
    if (S.empty()) return false; // shouldn't happen
    cout << "? " << S.size();
    for (int v : S) cout << " " << v;
    cout << endl;
    cout.flush();
    string resp;
    if (!(cin >> resp)) exit(0);
    return resp == "YES";
}

bool guess(int g) {
    cout << "! " << g << endl;
    cout.flush();
    string resp;
    if (!(cin >> resp)) exit(0);
    return resp == ":)";
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<int> cand(n);
    iota(cand.begin(), cand.end(), 1);
    shuffle(cand.begin(), cand.end(), rng);
    
    auto split_four = [&](const vector<int>& v, array<vector<int>,4>& g){
        g = {};
        for (int i = 0; i < (int)v.size(); ++i) {
            g[i % 4].push_back(v[i]);
        }
    };
    
    auto merge_keep = [&](const array<vector<int>,4>& g, int excludeIdx){
        vector<int> res;
        for (int i = 0; i < 4; ++i) if (i != excludeIdx) {
            res.insert(res.end(), g[i].begin(), g[i].end());
        }
        return res;
    };

    auto do_round = [&](vector<int>& v)->bool{
        if ((int)v.size() <= 3) return false;
        array<vector<int>,4> g;
        split_four(v, g);
        vector<int> A = g[0];
        A.insert(A.end(), g[1].begin(), g[1].end());
        vector<int> B = g[0];
        B.insert(B.end(), g[2].begin(), g[2].end());
        bool a1 = ask(A);
        bool a2 = ask(B);
        int excludeIdx = -1;
        if (a1 && a2) excludeIdx = 3;          // YY -> exclude g3
        else if (a1 && !a2) excludeIdx = 2;    // YN -> exclude g2
        else if (!a1 && a2) excludeIdx = 1;    // NY -> exclude g1
        else excludeIdx = 0;                   // NN -> exclude g0
        v = merge_keep(g, excludeIdx);
        shuffle(v.begin(), v.end(), rng);
        return true;
    };
    
    auto small_phase = [&](vector<int>& v){
        // Reduce to at most 2 candidates using repeated singleton checks.
        // If we find the answer, we guess and exit.
        while ((int)v.size() > 2) {
            bool changed = false;
            vector<int> nv;
            for (int i = 0; i < (int)v.size(); ++i) {
                int x = v[i];
                vector<int> S = {x};
                bool a1 = ask(S);
                bool a2 = ask(S);
                if (a1 == a2) {
                    if (a1) {
                        // Confident it's x
                        if (guess(x)) return;
                        // If wrong (shouldn't happen due to guarantees), continue.
                    } else {
                        // Definitely not x
                        changed = true;
                    }
                } else {
                    // Ambiguous, keep it
                    nv.push_back(x);
                }
                if ((int)nv.size() + ((int)v.size() - i - 1) <= 2) {
                    // Early break if remaining can be truncated to <= 2
                    for (int j = i + 1; j < (int)v.size(); ++j) nv.push_back(v[j]);
                    break;
                }
            }
            v = nv;
            if (!changed && (int)v.size() > 2) {
                // If no progress, perform a 4-group round once
                if (!do_round(v)) break;
            }
        }
    };
    
    while ((int)cand.size() > 2) {
        if ((int)cand.size() <= 20) {
            small_phase(cand);
            break;
        }
        do_round(cand);
    }

    if ((int)cand.size() == 2) {
        if (guess(cand[0])) return 0;
        guess(cand[1]);
        return 0;
    } else if ((int)cand.size() == 1) {
        guess(cand[0]);
        return 0;
    } else if (!cand.empty()) {
        // Fallback: try small phase then guess remaining
        small_phase(cand);
        if ((int)cand.size() == 2) {
            if (guess(cand[0])) return 0;
            guess(cand[1]);
        } else if ((int)cand.size() == 1) {
            guess(cand[0]);
        } else {
            // As last resort, random guesses within remaining budget
            for (int x : cand) {
                if (guess(x)) return 0;
            }
        }
    }

    return 0;
}