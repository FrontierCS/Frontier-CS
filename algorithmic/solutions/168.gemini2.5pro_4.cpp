#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <chrono>
#include <random>

using namespace std;

int N;
int M, H;
vector<int> A;
vector<vector<int>> adj;

struct SolutionState {
    vector<int> parent;
    vector<vector<int>> children;
    long long score;

    SolutionState() : score(0) {}

    void resize(int n) {
        parent.resize(n, -1);
        children.resize(n);
    }

    void build_children() {
        for (int i = 0; i < N; ++i) {
            children[i].clear();
        }
        for (int i = 0; i < N; ++i) {
            if (parent[i] != -1) {
                children[parent[i]].push_back(i);
            }
        }
    }
    
    void calculate_total_score() {
        vector<int> depth(N, 0);
        vector<int> q;
        for (int i = 0; i < N; ++i) {
            if (parent[i] == -1) {
                depth[i] = 0;
                q.push_back(i);
            }
        }
        int head = 0;
        while(head < q.size()){
            int u = q[head++];
            for(int v : children[u]){
                depth[v] = depth[u] + 1;
                q.push_back(v);
            }
        }
        score = 0;
        for (int i = 0; i < N; i++) {
            score += (long long)(depth[i] + 1) * A[i];
        }
    }
};

void get_subtree_properties_dfs(int u, const vector<vector<int>>& children, long long& subtree_A_sum, int& max_rel_depth, int current_rel_depth) {
    subtree_A_sum += A[u];
    max_rel_depth = max(max_rel_depth, current_rel_depth);
    for (int v : children[u]) {
        get_subtree_properties_dfs(v, children, subtree_A_sum, max_rel_depth, current_rel_depth + 1);
    }
}

int get_depth(int u, const vector<int>& parent) {
    int d = 0;
    while (parent[u] != -1) {
        u = parent[u];
        d++;
    }
    return d;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    auto start_time = chrono::high_resolution_clock::now();

    cin >> N >> M >> H;
    A.resize(N);
    adj.resize(N);

    for (int i = 0; i < N; ++i) cin >> A[i];
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    for (int i = 0; i < N; ++i) {
        int x, y;
        cin >> x >> y;
    }

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    SolutionState best_sol;
    best_sol.resize(N);
    
    // Initial solution
    {
        vector<int> p(N);
        iota(p.begin(), p.end(), 0);
        sort(p.begin(), p.end(), [&](int i, int j) {
            return A[i] < A[j];
        });

        vector<bool> assigned(N, false);
        for (int i = 0; i < N; ++i) {
            int root = p[i];
            if (assigned[root]) continue;
            
            best_sol.parent[root] = -1;
            assigned[root] = true;
            vector<pair<int, int>> q;
            q.push_back({root, 0});
            int head = 0;
            while(head < q.size()){
                auto [u, d] = q[head++];
                if(d >= H) continue;
                for(int v : adj[u]){
                    if(!assigned[v]){
                        assigned[v] = true;
                        best_sol.parent[v] = u;
                        q.push_back({v, d + 1});
                    }
                }
            }
        }
    }

    best_sol.build_children();
    best_sol.calculate_total_score();
    
    SolutionState current_sol = best_sol;
    
    double T_start = 500;
    double T_end = 0.1;
    
    while (true) {
        auto now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(now - start_time).count();
        if (elapsed > 1.95) break;

        double progress = elapsed / 1.95;
        double T = T_start * pow(T_end / T_start, progress);

        int v = rng() % N;
        
        vector<int> candidates = adj[v];
        candidates.push_back(-1);
        int p_new = candidates[rng() % candidates.size()];
        int p_old = current_sol.parent[v];
        if (p_new == p_old) continue;

        if (p_new != -1) {
            bool is_ancestor = false;
            int curr = p_new;
            while (curr != -1) {
                if (curr == v) {
                    is_ancestor = true;
                    break;
                }
                curr = current_sol.parent[curr];
            }
            if (is_ancestor) continue;
        }
        
        int d_v = get_depth(v, current_sol.parent);
        int d_p_new = (p_new == -1) ? -1 : get_depth(p_new, current_sol.parent);
        int new_d_v = d_p_new + 1;
        
        long long subtree_A_sum = 0;
        int max_rel_depth = 0;
        get_subtree_properties_dfs(v, current_sol.children, subtree_A_sum, max_rel_depth, 0);
        
        if (new_d_v + max_rel_depth > H) continue;

        long long score_delta = (long long)(new_d_v - d_v) * subtree_A_sum;

        if (score_delta >= 0 || (T > 1e-9 && exp(score_delta / T) > (double)rng() / rng.max())) {
            
            if (p_old != -1) {
                auto& children_old = current_sol.children[p_old];
                children_old.erase(remove(children_old.begin(), children_old.end(), v), children_old.end());
            }
            current_sol.parent[v] = p_new;
            if (p_new != -1) {
                current_sol.children[p_new].push_back(v);
            }
            current_sol.score += score_delta;
            
            if (current_sol.score > best_sol.score) {
                best_sol.score = current_sol.score;
                best_sol.parent = current_sol.parent;
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << best_sol.parent[i] << (i == N - 1 ? "" : " ");
    }
    cout << endl;

    return 0;
}