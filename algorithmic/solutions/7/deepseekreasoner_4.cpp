#include <bits/stdc++.h>
using namespace std;

struct State {
    int l, cmpL, cmpR;
    State(int l = 0, int cmpL = 0, int cmpR = 0) : l(l), cmpL(cmpL), cmpR(cmpR) {}
    bool operator<(const State& other) const {
        if (l != other.l) return l < other.l;
        if (cmpL != other.cmpL) return cmpL < other.cmpL;
        return cmpR < other.cmpR;
    }
};

int main() {
    int L, R;
    cin >> L >> R;
    
    string L_bin, R_bin;
    // binary representation without leading zeros
    for (int x = L; x > 0; x >>= 1) L_bin.push_back('0' + (x & 1));
    for (int x = R; x > 0; x >>= 1) R_bin.push_back('0' + (x & 1));
    reverse(L_bin.begin(), L_bin.end());
    reverse(R_bin.begin(), R_bin.end());
    
    int lenL = L_bin.size();
    int lenR = R_bin.size();
    
    map<State, int> state_map;
    vector<State> state_list;
    vector<vector<int>> trans;       // trans[id][0/1] -> target id or -1
    vector<bool> accepting;
    
    // start state (id 0)
    state_list.push_back(State(0, 0, 0));
    accepting.push_back(false);
    trans.push_back({-1, -1});
    
    auto get_id = [&](const State& s) -> int {
        if (state_map.count(s)) return state_map[s];
        int id = state_list.size();
        state_map[s] = id;
        state_list.push_back(s);
        accepting.push_back(false);
        trans.push_back({-1, -1});
        return id;
    };
    
    // transition from start on '1'
    {
        char bit = '1';
        int cmpL = (bit < L_bin[0] ? 0 : (bit == L_bin[0] ? 1 : 2));
        int cmpR = (bit < R_bin[0] ? 0 : (bit == R_bin[0] ? 1 : 2));
        State first(1, cmpL, cmpR);
        int id1 = get_id(first);
        trans[0][1] = id1;
    }
    
    queue<int> q;
    q.push(1);   // first state id
    
    while (!q.empty()) {
        int id = q.front(); q.pop();
        State s = state_list[id];
        if (s.l == lenR) continue;   // no outgoing edges
        
        for (int b = 0; b <= 1; ++b) {
            char bit_char = (b == 0 ? '0' : '1');
            int new_l = s.l + 1;
            
            int new_cmpL;
            if (s.cmpL == 0) new_cmpL = 0;
            else if (s.cmpL == 2) new_cmpL = 2;
            else { // s.cmpL == 1
                if (new_l <= lenL) {
                    char L_bit = L_bin[s.l]; // next bit of L
                    if (bit_char < L_bit) new_cmpL = 0;
                    else if (bit_char == L_bit) new_cmpL = 1;
                    else new_cmpL = 2;
                } else {
                    new_cmpL = 2;
                }
            }
            
            int new_cmpR;
            if (s.cmpR == 0) new_cmpR = 0;
            else if (s.cmpR == 2) new_cmpR = 2;
            else { // s.cmpR == 1
                if (new_l <= lenR) {
                    char R_bit = R_bin[s.l];
                    if (bit_char < R_bit) new_cmpR = 0;
                    else if (bit_char == R_bit) new_cmpR = 1;
                    else new_cmpR = 2;
                } else {
                    new_cmpR = 2; // should not happen
                }
            }
            
            State next_s(new_l, new_cmpL, new_cmpR);
            int next_id = get_id(next_s);
            trans[id][b] = next_id;
            if (next_id == state_list.size() - 1) { // newly created
                q.push(next_id);
            }
        }
    }
    
    // mark accepting states
    for (size_t i = 1; i < state_list.size(); ++i) {
        State s = state_list[i];
        if (s.l < lenL) {
            accepting[i] = false;
        } else if (s.l == lenL) {
            accepting[i] = (s.cmpL != 0);
        } else if (s.l < lenR) {
            accepting[i] = true;
        } else if (s.l == lenR) {
            accepting[i] = (s.cmpR != 2);
        } else {
            accepting[i] = false;
        }
    }
    
    int n_old = state_list.size();
    // Minimization (table-filling)
    vector<vector<bool>> dist(n_old, vector<bool>(n_old, false));
    // initialize with accepting differences
    for (int i = 0; i < n_old; ++i) {
        for (int j = i+1; j < n_old; ++j) {
            if (accepting[i] != accepting[j]) {
                dist[i][j] = dist[j][i] = true;
            }
        }
    }
    // propagation
    bool changed;
    do {
        changed = false;
        for (int i = 0; i < n_old; ++i) {
            for (int j = i+1; j < n_old; ++j) {
                if (dist[i][j]) continue;
                for (int b = 0; b < 2; ++b) {
                    int ni = trans[i][b];
                    int nj = trans[j][b];
                    if (ni == -1 && nj == -1) continue;
                    if ((ni == -1) != (nj == -1)) {
                        dist[i][j] = dist[j][i] = true;
                        changed = true;
                        break;
                    }
                    if (ni != -1 && nj != -1 && dist[ni][nj]) {
                        dist[i][j] = dist[j][i] = true;
                        changed = true;
                        break;
                    }
                }
            }
        }
    } while (changed);
    
    // build equivalence classes, keeping start state (0) alone
    vector<int> class_id(n_old, -1);
    class_id[0] = 0;
    int class_cnt = 1;
    for (int i = 1; i < n_old; ++i) {
        bool found = false;
        for (int c = 0; c < class_cnt; ++c) {
            // find a representative with class c (c>0 or representative !=0)
            int rep = -1;
            for (int k = 0; k < n_old; ++k) {
                if (class_id[k] == c) {
                    rep = k;
                    break;
                }
            }
            if (rep != -1 && !dist[i][rep]) {
                class_id[i] = c;
                found = true;
                break;
            }
        }
        if (!found) {
            class_id[i] = class_cnt++;
        }
    }
    
    int m = class_cnt;   // number of states in minimal DFA
    vector<bool> min_accepting(m, false);
    vector<array<int,2>> min_trans(m, {-1,-1});
    // build transitions from representatives
    for (int i = 0; i < n_old; ++i) {
        int c = class_id[i];
        if (accepting[i]) min_accepting[c] = true;
        for (int b = 0; b < 2; ++b) {
            if (trans[i][b] != -1) {
                int target_c = class_id[trans[i][b]];
                min_trans[c][b] = target_c;
            }
        }
    }
    
    // Transform to NFA with single sink
    int sink_id = m;
    int n_final = m + 1;
    vector<vector<pair<int,int>>> edges(n_final);
    
    for (int i = 0; i < m; ++i) {
        for (int b = 0; b < 2; ++b) {
            int target = min_trans[i][b];
            if (target != -1) {
                edges[i].emplace_back(target, b);
                if (min_accepting[target]) {
                    edges[i].emplace_back(sink_id, b);
                }
            }
        }
    }
    
    // Output
    cout << n_final << "\n";
    for (int i = 0; i < n_final; ++i) {
        cout << edges[i].size();
        for (auto& e : edges[i]) {
            cout << " " << e.first + 1 << " " << e.second;
        }
        cout << "\n";
    }
    
    return 0;
}