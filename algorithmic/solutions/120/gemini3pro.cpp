#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <map>
#include <set>
#include <random>
#include <cassert>
#include <tuple>
#include <chrono>

using namespace std;

// Globals
int N = 100;
int adj[101][101]; // 0: unknown, 1: no edge (0), 2: edge (1)
// Internal logic uses 0-based for vector indices in subroutines, but 1-based for vertex labels.

int known_edge(int u, int v) {
    if (adj[u][v] == 2) return 1;
    if (adj[u][v] == 1) return 0;
    return -1;
}

void set_edge(int u, int v, int val) {
    adj[u][v] = val ? 2 : 1;
    adj[v][u] = val ? 2 : 1;
}

int query(int a, int b, int c) {
    cout << "? " << a << " " << b << " " << c << endl;
    int ans;
    cin >> ans;
    return ans;
}

// Phase 1 data
int p1_type[101]; // 0: unk, 1: Z, 2: F, 3: O, 4: T
bool e01_known = false;
int e01_val = -1;
bool node_resolved[101]; // true if e0i, e1i known relative to 1,2
int e0i_val[101]; 
int e1i_val[101];

void resolve_node(int k) {
    if (node_resolved[k]) return;
    int r = -1;
    for (int i = 3; i <= N; i++) {
        if (i != k && node_resolved[i]) {
            r = i;
            break;
        }
    }
    // If no resolved reference found, we might need to assume one (not expected with N=100)
    if (r == -1) {
        // Fallback: pick any other node
        r = (k == 3) ? 4 : 3;
        // Assume r is (0,0) type for consistency, can be flipped globally later? 
        // No, we must be exact. But this case is extremely unlikely.
        e0i_val[r] = 0; e1i_val[r] = 0; node_resolved[r] = true;
    }

    int q0 = query(1, r, k); 
    int q1 = query(2, r, k); 
    
    int diff = q0 - q1;
    int term_r = e0i_val[r] - e1i_val[r];
    int delta = diff - term_r;
    
    // e0k + e1k = 1 for mixed nodes
    if (delta == 1) {
        e0i_val[k] = 1; e1i_val[k] = 0;
    } else {
        e0i_val[k] = 0; e1i_val[k] = 1;
    }
    node_resolved[k] = true;
    
    // Also derive edge r-k
    set_edge(r, k, q0 - e0i_val[r] - e0i_val[k]);
}

int get_edge_via_0(int u, int v) {
    if (!node_resolved[u]) resolve_node(u);
    if (!node_resolved[v]) resolve_node(v);
    int ans = query(1, u, v); 
    return ans - e0i_val[u] - e0i_val[v];
}

map<vector<int>, vector<int>> k5_map;
vector<tuple<int,int,int>> k5_triples;

void init_k5() {
    vector<tuple<int,int,int>> all_triples;
    for(int i=0;i<5;i++) for(int j=i+1;j<5;j++) for(int k=j+1;k<5;k++)
        all_triples.emplace_back(i,j,k);
        
    mt19937 rng(123);
    int best_max_sz = 10000;
    
    for (int iter=0; iter<50; iter++) {
        vector<int> idx(10);
        iota(idx.begin(), idx.end(), 0);
        shuffle(idx.begin(), idx.end(), rng);
        vector<tuple<int,int,int>> current_triples;
        for(int i=0; i<6; ++i) current_triples.push_back(all_triples[idx[i]]);
        
        map<vector<int>, vector<int>> temp_map;
        int max_sz = 0;
        
        for (int m=0; m<1024; m++) {
            vector<int> res;
            auto edge = [&](int u, int v) {
                int bit = 0;
                if (u > v) swap(u, v);
                if (u==0 && v==1) bit=0;
                else if (u==0 && v==2) bit=1;
                else if (u==0 && v==3) bit=2;
                else if (u==0 && v==4) bit=3;
                else if (u==1 && v==2) bit=4;
                else if (u==1 && v==3) bit=5;
                else if (u==1 && v==4) bit=6;
                else if (u==2 && v==3) bit=7;
                else if (u==2 && v==4) bit=8;
                else if (u==3 && v==4) bit=9;
                return (m >> bit) & 1;
            };
            for (auto& t : current_triples) {
                res.push_back(edge(get<0>(t), get<1>(t)) + edge(get<1>(t), get<2>(t)) + edge(get<0>(t), get<2>(t)));
            }
            temp_map[res].push_back(m);
            max_sz = max(max_sz, (int)temp_map[res].size());
        }
        
        if (max_sz < best_max_sz) {
            best_max_sz = max_sz;
            k5_map = temp_map;
            k5_triples = current_triples;
        }
    }
}

map<vector<int>, vector<int>> k4_map;
void init_k4() {
    for (int m=0; m<64; m++) {
        vector<int> res;
        auto edge = [&](int u, int v) {
            int bit = 0;
            if (u==0 && v==1) bit=0;
            else if (u==0 && v==2) bit=1;
            else if (u==0 && v==3) bit=2;
            else if (u==1 && v==2) bit=3;
            else if (u==1 && v==3) bit=4;
            else if (u==2 && v==3) bit=5;
            return (m >> bit) & 1;
        };
        res.push_back(edge(0,1)+edge(1,2)+edge(0,2));
        res.push_back(edge(0,1)+edge(1,3)+edge(0,3));
        res.push_back(edge(0,2)+edge(2,3)+edge(0,3));
        res.push_back(edge(1,2)+edge(2,3)+edge(1,3));
        k4_map[res].push_back(m);
    }
}

int main() {
    init_k5();
    init_k4();
    
    // Phase 1: Determine e01 and classify nodes
    for (int k=3; k<=N; ++k) {
        int ans = query(1, 2, k);
        if (ans == 0) { p1_type[k] = 1; e01_val = 0; }
        else if (ans == 3) { p1_type[k] = 2; e01_val = 1; }
        else if (ans == 1) { p1_type[k] = 3; }
        else if (ans == 2) { p1_type[k] = 4; }
    }
    
    if (e01_val == -1) {
        vector<int> O_nodes, T_nodes;
        for(int k=3; k<=N; ++k) {
            if (p1_type[k]==3) O_nodes.push_back(k);
            if (p1_type[k]==4) T_nodes.push_back(k);
        }
        bool determined = false;
        if (O_nodes.size() >= 2) {
             int limit = min((int)O_nodes.size(), 5); 
             for (int i=0; i<limit && !determined; ++i) {
                 for (int j=i+1; j<limit && !determined; ++j) {
                     int u = O_nodes[i], v = O_nodes[j];
                     if (query(1, u, v) - query(2, u, v) != 0) {
                         e01_val = 0; determined = true;
                     }
                 }
             }
             if (!determined && O_nodes.size() >= 3) { e01_val = 1; determined = true; }
        }
        if (!determined && T_nodes.size() >= 2) {
             int limit = min((int)T_nodes.size(), 5); 
             for (int i=0; i<limit && !determined; ++i) {
                 for (int j=i+1; j<limit && !determined; ++j) {
                     int u = T_nodes[i], v = T_nodes[j];
                     if (query(1, u, v) - query(2, u, v) != 0) {
                         e01_val = 1; determined = true;
                     }
                 }
             }
             if (!determined && T_nodes.size() >= 3) { e01_val = 0; determined = true; }
        }
        if (!determined) e01_val = 0; 
    }
    
    set_edge(1, 2, e01_val);
    e0i_val[1] = 0; e1i_val[1] = e01_val; 
    e0i_val[2] = e01_val; e1i_val[2] = 0;
    node_resolved[1] = true; node_resolved[2] = true;
    
    for (int k=3; k<=N; ++k) {
        if (p1_type[k] == 1) { 
            e0i_val[k] = 0; e1i_val[k] = 0; node_resolved[k] = true; set_edge(1, k, 0); set_edge(2, k, 0);
        } else if (p1_type[k] == 2) { 
            e0i_val[k] = 1; e1i_val[k] = 1; node_resolved[k] = true; set_edge(1, k, 1); set_edge(2, k, 1);
        } else if (p1_type[k] == 3) { 
            if (e01_val == 1) { 
                e0i_val[k] = 0; e1i_val[k] = 0; node_resolved[k] = true; set_edge(1, k, 0); set_edge(2, k, 0);
            } else node_resolved[k] = false;
        } else if (p1_type[k] == 4) { 
            if (e01_val == 0) { 
                e0i_val[k] = 1; e1i_val[k] = 1; node_resolved[k] = true; set_edge(1, k, 1); set_edge(2, k, 1);
            } else node_resolved[k] = false;
        }
    }
    
    vector<int> unknown_nodes;
    for(int i=3; i<=N; ++i) unknown_nodes.push_back(i);
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    
    // Phase 2: K5 Packing
    while (true) {
        shuffle(unknown_nodes.begin(), unknown_nodes.end(), rng);
        vector<int> k5;
        for (int u : unknown_nodes) {
            bool ok = true;
            for (int v : k5) if (known_edge(u, v) != -1) { ok = false; break; }
            if (ok) {
                k5.push_back(u);
                if (k5.size() == 5) break;
            }
        }
        if (k5.size() < 5) break; 
        
        vector<int> res;
        for (auto& t : k5_triples) 
            res.push_back(query(k5[get<0>(t)], k5[get<1>(t)], k5[get<2>(t)]));
        
        vector<int> candidates = k5_map[res];
        vector<tuple<int,int,int>> all_trips;
        for(int i=0;i<5;i++) for(int j=i+1;j<5;j++) for(int k=j+1;k<5;k++) all_trips.emplace_back(i,j,k);
        
        // Save base 6 triples to reset later
        auto base_triples = k5_triples;

        while (candidates.size() > 1) {
             tuple<int,int,int> next_triple;
             bool found = false;
             for (auto& cand_t : all_trips) {
                 bool used = false;
                 for (auto& used_t : k5_triples) if (used_t == cand_t) used = true;
                 if (!used) {
                     int val0 = -1;
                     bool splits = false;
                     for (int m : candidates) {
                          int u = get<0>(cand_t), v = get<1>(cand_t), w = get<2>(cand_t);
                          auto get_val = [&](int mask, int a, int b) {
                              if (a>b) swap(a,b);
                              int bit=0;
                                if (a==0 && b==1) bit=0; else if (a==0 && b==2) bit=1; else if (a==0 && b==3) bit=2; else if (a==0 && b==4) bit=3;
                                else if (a==1 && b==2) bit=4; else if (a==1 && b==3) bit=5; else if (a==1 && b==4) bit=6;
                                else if (a==2 && b==3) bit=7; else if (a==2 && b==4) bit=8; else if (a==3 && b==4) bit=9;
                              return (mask>>bit)&1;
                          };
                          int ans = get_val(m, u, v) + get_val(m, v, w) + get_val(m, u, w);
                          if (val0 == -1) val0 = ans;
                          if (ans != val0) splits = true;
                     }
                     if (splits) {
                         next_triple = cand_t; found = true; k5_triples.push_back(next_triple); break;
                     }
                 }
             }
             
             if (found) {
                 int ans = query(k5[get<0>(next_triple)], k5[get<1>(next_triple)], k5[get<2>(next_triple)]);
                 vector<int> next_cands;
                 for (int m : candidates) {
                      int u = get<0>(next_triple), v = get<1>(next_triple), w = get<2>(next_triple);
                      auto get_val = [&](int mask, int a, int b) {
                          if (a>b) swap(a,b);
                          int bit=0;
                            if (a==0 && b==1) bit=0; else if (a==0 && b==2) bit=1; else if (a==0 && b==3) bit=2; else if (a==0 && b==4) bit=3;
                            else if (a==1 && b==2) bit=4; else if (a==1 && b==3) bit=5; else if (a==1 && b==4) bit=6;
                            else if (a==2 && b==3) bit=7; else if (a==2 && b==4) bit=8; else if (a==3 && b==4) bit=9;
                          return (mask>>bit)&1;
                      };
                      if (get_val(m, u, v) + get_val(m, v, w) + get_val(m, u, w) == ans) next_cands.push_back(m);
                 }
                 candidates = next_cands;
             } else {
                 int val = get_edge_via_0(k5[0], k5[1]);
                 vector<int> next_cands;
                 for (int m : candidates) if ((m&1) == val) next_cands.push_back(m);
                 candidates = next_cands;
             }
        }
        
        int m = candidates[0];
        auto set_k5_edge = [&](int u_idx, int v_idx, int bit) { set_edge(k5[u_idx], k5[v_idx], (m>>bit)&1); };
        set_k5_edge(0,1,0); set_k5_edge(0,2,1); set_k5_edge(0,3,2); set_k5_edge(0,4,3);
        set_k5_edge(1,2,4); set_k5_edge(1,3,5); set_k5_edge(1,4,6);
        set_k5_edge(2,3,7); set_k5_edge(2,4,8); set_k5_edge(3,4,9);
        k5_triples = base_triples;
    }
    
    // Fallback Phase 3: K4 Packing
    while (true) {
        shuffle(unknown_nodes.begin(), unknown_nodes.end(), rng);
        vector<int> k4;
        for (int u : unknown_nodes) {
            bool ok = true;
            for (int v : k4) if (known_edge(u, v) != -1) { ok = false; break; }
            if (ok) { k4.push_back(u); if (k4.size() == 4) break; }
        }
        if (k4.size() < 4) break;
        
        vector<int> res;
        res.push_back(query(k4[0], k4[1], k4[2]));
        res.push_back(query(k4[0], k4[1], k4[3]));
        res.push_back(query(k4[0], k4[2], k4[3]));
        res.push_back(query(k4[1], k4[2], k4[3]));
        
        vector<int> candidates = k4_map[res];
        if (candidates.size() > 1) {
            int val = get_edge_via_0(k4[0], k4[1]);
            vector<int> next;
            for (int m : candidates) if ((m&1) == val) next.push_back(m);
            candidates = next;
            if (candidates.size() > 1) {
                val = get_edge_via_0(k4[0], k4[2]);
                next.clear();
                for (int m : candidates) if (((m>>1)&1) == val) next.push_back(m);
                candidates = next;
            }
        }
        
        int m = candidates[0];
        set_edge(k4[0], k4[1], (m>>0)&1); set_edge(k4[0], k4[2], (m>>1)&1); set_edge(k4[0], k4[3], (m>>2)&1);
        set_edge(k4[1], k4[2], (m>>3)&1); set_edge(k4[1], k4[3], (m>>4)&1); set_edge(k4[2], k4[3], (m>>5)&1);
    }
    
    // Final cleanup
    for (int i=3; i<=N; ++i) {
        for (int j=i+1; j<=N; ++j) {
            if (known_edge(i, j) == -1) {
                set_edge(i, j, get_edge_via_0(i, j));
            }
        }
    }
    
    cout << "!" << endl;
    for (int i=1; i<=N; ++i) {
        string s = "";
        for (int j=1; j<=N; ++j) {
            if (i==j) s += "0";
            else s += (known_edge(i, j) == 1 ? "1" : "0");
        }
        cout << s << endl;
    }
    
    return 0;
}