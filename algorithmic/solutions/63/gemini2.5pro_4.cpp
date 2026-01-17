#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

int N, M;
std::vector<std::pair<int, int>> edges;

bool ask_query(const std::vector<int>& dirs) {
    std::cout << "0";
    for (int i = 0; i < M; ++i) {
        std::cout << " " << dirs[i];
    }
    std::cout << std::endl;
    int response;
    std::cin >> response;
    return response == 1;
}

void answer(int a, int b) {
    std::cout << "1 " << a << " " << b << std::endl;
}

void bfs(int start_node, const std::vector<std::vector<int>>& adj, std::vector<bool>& reachable) {
    std::vector<int> q;
    q.reserve(N);
    q.push_back(start_node);
    reachable[start_node] = true;
    int head = 0;
    while(head < q.size()){
        int u = q[head++];
        for(int v : adj[u]){
            if(!reachable[v]){
                reachable[v] = true;
                q.push_back(v);
            }
        }
    }
}


int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> N >> M;
    edges.resize(M);
    for (int i = 0; i < M; ++i) {
        std::cin >> edges[i].first >> edges[i].second;
    }

    // Part 1: Find a working orientation
    std::vector<int> O_work(M);
    bool path_found = false;

    // Try all U_i -> V_i (dir=0)
    std::fill(O_work.begin(), O_work.end(), 0);
    if (ask_query(O_work)) {
        path_found = true;
    } else {
        // Try all V_i -> U_i (dir=1)
        std::fill(O_work.begin(), O_work.end(), 1);
        if (ask_query(O_work)) {
            path_found = true;
        }
    }

    if (!path_found) {
        std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
        std::uniform_int_distribution<int> distrib(0, 1);
        for (int i = 0; i < 30 && !path_found; ++i) {
            for (int j = 0; j < M; ++j) {
                O_work[j] = distrib(rng);
            }
            if (ask_query(O_work)) {
                path_found = true;
            }
        }
    }

    // Part 2: Find a critical edge
    std::vector<int> O_base = O_work;
    int crit_edge_idx = -1;
    int L = 0, R = M - 1;
    while(L < R) {
        int mid = L + (R - L) / 2;
        std::vector<int> O_test = O_base;
        for(int i = 0; i <= mid; ++i) {
            O_test[i] = 1 - O_test[i];
        }
        if(!ask_query(O_test)) {
            R = mid;
        } else {
            L = mid + 1;
        }
    }
    crit_edge_idx = L;
    
    std::vector<int> O_crit = O_base;
    for(int i = 0; i < crit_edge_idx; ++i) {
        O_crit[i] = 1 - O_crit[i];
    }
    
    // Part 3: Compute candidate sets for A and B
    int u, v;
    if (O_crit[crit_edge_idx] == 0) {
        u = edges[crit_edge_idx].first;
        v = edges[crit_edge_idx].second;
    } else {
        u = edges[crit_edge_idx].second;
        v = edges[crit_edge_idx].first;
    }

    std::vector<std::vector<int>> adj(N), rev_adj(N);
    for(int i = 0; i < M; ++i) {
        if (i == crit_edge_idx) continue;
        int U = edges[i].first;
        int V = edges[i].second;
        if(O_crit[i] == 0) {
            adj[U].push_back(V);
            rev_adj[V].push_back(U);
        } else {
            adj[V].push_back(U);
            rev_adj[U].push_back(V);
        }
    }
    
    std::vector<bool> cand_A_mask(N, false), cand_B_mask(N, false);
    bfs(u, rev_adj, cand_A_mask);
    bfs(v, adj, cand_B_mask);

    std::vector<int> cand_A_vec, cand_B_vec;
    for(int i=0; i<N; ++i) {
        if(cand_A_mask[i]) cand_A_vec.push_back(i);
        if(cand_B_mask[i]) cand_B_vec.push_back(i);
    }
    
    // Part 4: Binary search for A
    int final_A;
    L = 0, R = cand_A_vec.size() - 1;
    while(L < R) {
        int mid = L + (R - L) / 2;
        std::vector<bool> S_mask(N, false);
        for (int i = 0; i <= mid; ++i) S_mask[cand_A_vec[i]] = true;

        std::vector<int> O_test(M);
        for (int i = 0; i < M; ++i) {
            int U = edges[i].first, V = edges[i].second;
            bool u_in_S = S_mask[U], v_in_S = S_mask[V];
            if (u_in_S && !v_in_S) O_test[i] = 1; // V->U, S is sink
            else if (!u_in_S && v_in_S) O_test[i] = 0; // U->V
            else O_test[i] = 0; // arbitrary
        }
        if (!ask_query(O_test)) R = mid; // A in S
        else L = mid + 1; // A not in S
    }
    final_A = cand_A_vec[L];

    // Part 5: Binary search for B
    int final_B;
    L = 0, R = cand_B_vec.size() - 1;
    while(L < R) {
        int mid = L + (R-L)/2;
        std::vector<bool> S_mask(N, false);
        for (int i = 0; i <= mid; ++i) S_mask[cand_B_vec[i]] = true;

        std::vector<int> O_test(M);
        for(int i=0; i<M; ++i) {
            int U = edges[i].first, V = edges[i].second;
            bool u_in_S = S_mask[U], v_in_S = S_mask[V];
            if(u_in_S && !v_in_S) O_test[i] = 0; // U->V, S is source
            else if(!u_in_S && v_in_S) O_test[i] = 1; // V->U
            else O_test[i] = 0; // arbitrary
        }
        if (!ask_query(O_test)) R = mid; // B in S
        else L = mid + 1; // B not in S
    }
    final_B = cand_B_vec[L];
    
    answer(final_A, final_B);

    return 0;
}