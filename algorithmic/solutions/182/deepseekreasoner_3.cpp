#include <iostream>
#include <vector>
#include <algorithm>
#include <ctime>
#include <cstdlib>
#include <chrono>
#include <climits>
#include <queue>

using namespace std;

const int MAXN = 10005;
const int MAXM = 500005;

struct Edge {
    int u, v;
    long long weight;
};

int N, M;
Edge edges[MAXM];
vector<int> adj[MAXN];

int sol[MAXN];       
int best_sol[MAXN];
int best_k = MAXN + 1;

long long dscore[MAXN]; 
int conf_change[MAXN];  
int comb_cov[MAXM];     

int uncov_stack[MAXM]; 
int uncov_pos[MAXM];   
int uncov_cnt = 0;

auto start_time = chrono::high_resolution_clock::now();

void add_uncov(int e_idx) {
    if (uncov_pos[e_idx] != -1) return;
    uncov_pos[e_idx] = uncov_cnt;
    uncov_stack[uncov_cnt++] = e_idx;
}

void remove_uncov(int e_idx) {
    int pos = uncov_pos[e_idx];
    if (pos == -1) return;
    int last_e = uncov_stack[--uncov_cnt];
    uncov_stack[pos] = last_e;
    uncov_pos[last_e] = pos;
    uncov_pos[e_idx] = -1;
}

void flip(int v) {
    sol[v] = 1 - sol[v];
    int direction = (sol[v] == 1) ? 1 : -1; 
    
    dscore[v] = -dscore[v];
    
    for (int e_idx : adj[v]) {
        int u = (edges[e_idx].u == v) ? edges[e_idx].v : edges[e_idx].u;
        long long w = edges[e_idx].weight;
        
        int old_cov = comb_cov[e_idx];
        int new_cov = old_cov + direction;
        comb_cov[e_idx] = new_cov;
        
        if (direction == 1) { 
            if (old_cov == 0) {
                dscore[u] -= w; 
                remove_uncov(e_idx);
            } else if (old_cov == 1) {
                dscore[u] += w;
            }
        } else { 
            if (new_cov == 0) {
                add_uncov(e_idx);
                dscore[u] += w;
            } else if (new_cov == 1) {
                dscore[u] -= w;
            }
        }
    }
}

void build() {
    uncov_cnt = 0;
    for (int i = 0; i < M; ++i) {
        uncov_pos[i] = -1;
        comb_cov[i] = 0;
        if (sol[edges[i].u]) comb_cov[i]++;
        if (sol[edges[i].v]) comb_cov[i]++;
        if (comb_cov[i] == 0) add_uncov(i);
    }
    
    for (int i = 1; i <= N; ++i) dscore[i] = 0;
    
    for (int i = 0; i < M; ++i) {
        long long w = edges[i].weight;
        int u = edges[i].u;
        int v = edges[i].v;
        
        if (comb_cov[i] == 0) {
            dscore[u] += w;
            dscore[v] += w;
        } else if (comb_cov[i] == 1) {
            if (sol[u]) dscore[u] -= w;
            else dscore[v] -= w;
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    srand(42); 

    if (!(cin >> N >> M)) return 0;
    
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        edges[i] = {u, v, 1};
        adj[u].push_back(i);
        adj[v].push_back(i);
    }
    
    vector<int> deg(N + 1, 0);
    vector<bool> cov_edge(M, false);
    for(int i=0; i<M; ++i) {
        deg[edges[i].u]++;
        deg[edges[i].v]++;
    }
    
    priority_queue<pair<int,int>> pq;
    for(int i=1; i<=N; ++i) pq.push({deg[i], i});
    
    int edges_left = M;
    vector<int> in_c(N + 1, 0);
    
    while (edges_left > 0 && !pq.empty()) {
        auto top = pq.top(); pq.pop();
        int d = top.first;
        int v = top.second;
        
        if (in_c[v]) continue;
        if (d != deg[v]) continue; 
        
        in_c[v] = 1;
        for (int e_idx : adj[v]) {
            if (!cov_edge[e_idx]) {
                cov_edge[e_idx] = true;
                edges_left--;
                int u = edges[e_idx].u;
                int nbr = (u == v) ? edges[e_idx].v : u;
                deg[nbr]--;
                pq.push({deg[nbr], nbr});
            }
        }
    }
    
    for(int i=1; i<=N; ++i) {
        sol[i] = in_c[i];
    }

    build(); 
    
    bool reduced = true;
    while(reduced) {
        reduced = false;
        for (int i=1; i<=N; ++i) {
            if (sol[i] == 1) {
                if (dscore[i] == 0) {
                    flip(i);
                    reduced = true;
                }
            }
        }
    }
    
    best_k = 0;
    for(int i=1; i<=N; ++i) {
        best_sol[i] = sol[i];
        if (best_sol[i]) best_k++;
    }
    
    long long step = 0;
    
    while (true) {
        auto now = chrono::high_resolution_clock::now();
        chrono::duration<double> elapsed = now - start_time;
        if (elapsed.count() > 1.95) break;
        
        for(int i=1; i<=N; ++i) sol[i] = best_sol[i];
        
        for(int i=0; i<M; ++i) edges[i].weight = 1;
        build(); 
        
        int best_rem_cand = -1;
        long long best_rem_score = LLONG_MIN;
        
        for(int i=1; i<=N; ++i) {
            if (sol[i]) {
                if (dscore[i] > best_rem_score) {
                    best_rem_score = dscore[i];
                    best_rem_cand = i;
                }
            }
        }
        
        if (best_rem_cand != -1) {
            flip(best_rem_cand);
            conf_change[best_rem_cand] = 1; 
        } else {
            break;
        }
        
        while (uncov_cnt > 0) {
            step++;
            if ((step & 1023) == 0) {
                if ((chrono::high_resolution_clock::now() - start_time).count() > 1.95) goto end_search;
            }
            
            int rand_idx = rand() % uncov_cnt;
            int e_idx = uncov_stack[rand_idx];
            int u = edges[e_idx].u;
            int v = edges[e_idx].v;
            
            int add_v = -1;
            if (dscore[u] > dscore[v]) add_v = u;
            else if (dscore[v] > dscore[u]) add_v = v;
            else {
                if (conf_change[u] < conf_change[v]) add_v = u;
                else add_v = v;
            }
            
            flip(add_v);
            conf_change[add_v] = step;
            
            int remove_v = -1;
            long long max_rem_score = LLONG_MIN;
            
            for (int k=0; k<50; ++k) {
                int r = (rand() % N) + 1;
                if (sol[r] && r != add_v) {
                    if (dscore[r] > max_rem_score) {
                        max_rem_score = dscore[r];
                        remove_v = r;
                    }
                }
            }
            
            if (remove_v == -1) {
                 for(int i=1; i<=N; ++i) {
                     if (sol[i] && i != add_v) {
                        if (dscore[i] > max_rem_score) {
                            max_rem_score = dscore[i];
                            remove_v = i;
                        }
                     }
                 }
            }
            
            if (remove_v != -1) {
                flip(remove_v);
                conf_change[remove_v] = step;
            }
            
            for (int i=0; i<uncov_cnt; ++i) {
                int ed = uncov_stack[i];
                edges[ed].weight++;
                dscore[edges[ed].u]++;
                dscore[edges[ed].v]++;
            }
        }
        
        best_k--;
        for(int i=1; i<=N; ++i) best_sol[i] = sol[i];
    }
    
    end_search:;
    
    for (int i=1; i<=N; ++i) {
        cout << best_sol[i] << "\n";
    }
    
    return 0;
}