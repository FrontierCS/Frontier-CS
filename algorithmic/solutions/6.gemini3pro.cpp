#include <vector>
#include <numeric>
#include <algorithm>
#include <set>
#include <cmath>
#include <random>
#include <chrono>

using namespace std;

static mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
static bool adj[45][45];
static vector<int> adj_list[45];
static int N_glob, M_glob;

struct Candidate {
    vector<int> row;
    int score;
};

inline bool is_adj_or_same(int u, int v) {
    if (u == v) return true;
    return adj[u][v];
}

std::vector<std::vector<int>> create_map(int N, int M,
    std::vector<int> A, std::vector<int> B) {
    
    N_glob = N;
    M_glob = M;
    
    for(int i=1; i<=N; ++i) {
        for(int j=1; j<=N; ++j) adj[i][j] = false;
        adj_list[i].clear();
    }
    
    for(int i=0; i<M; ++i) {
        int u = A[i];
        int v = B[i];
        adj[u][v] = adj[v][u] = true;
        adj_list[u].push_back(v);
        adj_list[v].push_back(u);
    }
    
    int lower_bound_K = ceil(sqrt(M/2.0));
    int node_bound = ceil(sqrt(N));
    int start_W = max({lower_bound_K, node_bound, 1});
    if (start_W < 2 && N > 1) start_W = 2;

    auto start_time = chrono::steady_clock::now();
    
    for (int W = start_W; W <= 240; ++W) {
        for (int attempt = 0; attempt < 5; ++attempt) {
            if (chrono::duration_cast<chrono::milliseconds>(chrono::steady_clock::now() - start_time).count() > 1900) {
                // Time limit approaching, stop trying
                break; 
            }

            vector<vector<int>> grid;
            set<pair<int,int>> covered_edges;
            set<int> covered_nodes;
            
            bool possible = true;
            for (int r = 0; r < 240; ++r) {
                if (covered_edges.size() == M && covered_nodes.size() == N) {
                    int H = grid.size();
                    int K = max(W, H);
                    vector<vector<int>> final_map(K, vector<int>(K));
                    for(int i=0; i<K; ++i) {
                        const vector<int>& src_row = (i < H) ? grid[i] : grid[H-1];
                        for(int j=0; j<K; ++j) {
                            final_map[i][j] = (j < W) ? src_row[j] : src_row[W-1];
                        }
                    }
                    return final_map;
                }
                
                if (r >= 240) { possible = false; break; }
                
                int beam_width = 40;
                vector<Candidate> beam;
                beam.push_back({{}, 0});
                
                for (int c = 0; c < W; ++c) {
                    vector<Candidate> next_beam;
                    int up_node = (r > 0) ? grid[r-1][c] : -1;
                    
                    for (const auto& cand : beam) {
                        int left_node = (c > 0) ? cand.row.back() : -1;
                        
                        vector<int> possibilities;
                        auto check_and_add = [&](int v) {
                            if (up_node != -1 && !is_adj_or_same(v, up_node)) return;
                            possibilities.push_back(v);
                        };
                        
                        if (left_node != -1) {
                            check_and_add(left_node);
                            for(int v : adj_list[left_node]) check_and_add(v);
                        } else if (up_node != -1) {
                            check_and_add(up_node);
                            for(int v : adj_list[up_node]) check_and_add(v);
                        } else {
                             // Random start
                             for(int k=0; k<10; ++k) {
                                 possibilities.push_back((rng() % N) + 1);
                             }
                        }
                        
                        if (possibilities.empty()) continue;
                        
                        sort(possibilities.begin(), possibilities.end());
                        possibilities.erase(unique(possibilities.begin(), possibilities.end()), possibilities.end());
                        shuffle(possibilities.begin(), possibilities.end(), rng);
                        if (possibilities.size() > 8) possibilities.resize(8);
                        
                        for (int v : possibilities) {
                            int score = cand.score;
                            if (covered_nodes.find(v) == covered_nodes.end()) score += 5000;
                             
                            if (left_node != -1 && left_node != v) {
                                int mn = min(left_node, v), mx = max(left_node, v);
                                if (covered_edges.find({mn, mx}) == covered_edges.end()) score += 100;
                            }
                            if (up_node != -1 && up_node != v) {
                                int mn = min(up_node, v), mx = max(up_node, v);
                                if (covered_edges.find({mn, mx}) == covered_edges.end()) score += 100;
                            }
                             
                            Candidate next = cand;
                            next.row.push_back(v);
                            next.score = score;
                            next_beam.push_back(next);
                        }
                    }
                    
                    if (next_beam.empty()) {
                        beam.clear();
                        break;
                    }
                    
                    sort(next_beam.begin(), next_beam.end(), [](const Candidate& a, const Candidate& b){
                        return a.score > b.score;
                    });
                    if (next_beam.size() > beam_width) next_beam.resize(beam_width);
                    beam = next_beam;
                }
                
                if (beam.empty()) {
                    possible = false;
                    break;
                }
                
                const auto& best_row = beam[0].row;
                grid.push_back(best_row);
                
                for (int c = 0; c < W; ++c) {
                    int v = best_row[c];
                    covered_nodes.insert(v);
                    if (c > 0) {
                        int u = best_row[c-1];
                        if (u != v) covered_edges.insert({min(u,v), max(u,v)});
                    }
                    if (r > 0) {
                        int u = grid[r-1][c];
                        if (u != v) covered_edges.insert({min(u,v), max(u,v)});
                    }
                }
            }
        }
    }
    return {};
}