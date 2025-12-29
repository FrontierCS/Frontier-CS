#include <bits/stdc++.h>
using namespace std;

const int DEPOT = 2000;
const int N_POINTS = 2001;
int dist[N_POINTS][N_POINTS];
int px[N_POINTS], py[N_POINTS];

int manhattan(int i, int j) {
    return abs(px[i] - px[j]) + abs(py[i] - py[j]);
}

double compute_length(const vector<int>& tour) {
    double len = 0;
    for (size_t i = 0; i + 1 < tour.size(); ++i)
        len += dist[tour[i]][tour[i+1]];
    return len;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // read orders
    for (int i = 0; i < 1000; ++i) {
        int a, b, c, d;
        cin >> a >> b >> c >> d;
        px[i] = a; py[i] = b;                     // pickup of order i
        px[1000 + i] = c; py[1000 + i] = d;       // delivery of order i
    }
    px[DEPOT] = 400; py[DEPOT] = 400;

    // precompute distance matrix
    for (int i = 0; i < N_POINTS; ++i)
        for (int j = 0; j < N_POINTS; ++j)
            dist[i][j] = manhattan(i, j);

    // compute standalone cost for each order
    vector<pair<double, int>> order_costs;
    for (int i = 0; i < 1000; ++i) {
        int pu = i;
        int dv = 1000 + i;
        double cost = dist[DEPOT][pu] + dist[pu][dv] + dist[dv][DEPOT];
        order_costs.emplace_back(cost, i);
    }
    sort(order_costs.begin(), order_costs.end());
    vector<int> chosen_orders;
    for (int i = 0; i < 50; ++i)
        chosen_orders.push_back(order_costs[i].second);

    const int NTRIALS = 5;
    const int N_PASSES = 5;

    random_device rd;
    mt19937 g(rd());

    double best_len = 1e18;
    vector<int> best_tour;
    vector<int> best_pu_pos(1000, -1), best_dv_pos(1000, -1);

    // try several random insertion orders
    for (int trial = 0; trial < NTRIALS; ++trial) {
        shuffle(chosen_orders.begin(), chosen_orders.end(), g);
        vector<int> tour = {DEPOT, DEPOT};
        vector<int> pu_pos(1000, -1), dv_pos(1000, -1);

        for (int ord : chosen_orders) {
            int pu = ord;
            int dv = 1000 + ord;
            int N = tour.size();
            double best_cost = 1e18;
            int best_p = -1, best_q = -1;

            // evaluate all insertion pairs (p,q) for this order
            for (int p = 0; p < N - 1; ++p) {
                double cost_p = dist[tour[p]][pu] + dist[pu][tour[p+1]] - dist[tour[p]][tour[p+1]];
                for (int q = p + 1; q < N - 1; ++q) {
                    int node_before, node_after;
                    if (q == p + 1) {
                        node_before = pu;
                        node_after = tour[p+1];
                    } else {
                        node_before = tour[q-1];
                        node_after = tour[q];
                    }
                    double cost_d = dist[node_before][dv] + dist[dv][node_after] - dist[node_before][node_after];
                    double total = cost_p + cost_d;
                    if (total < best_cost) {
                        best_cost = total;
                        best_p = p;
                        best_q = q;
                    }
                }
            }

            // perform the insertion
            tour.insert(tour.begin() + best_p + 1, pu);
            tour.insert(tour.begin() + best_q + 1, dv);
            pu_pos[ord] = best_p + 1;
            dv_pos[ord] = best_q + 1;
        }

        double len = compute_length(tour);
        if (len < best_len) {
            best_len = len;
            best_tour = tour;
            best_pu_pos = pu_pos;
            best_dv_pos = dv_pos;
        }
    }

    // local improvement by relocating single points
    for (int pass = 0; pass < N_PASSES; ++pass) {
        bool improved = false;
        for (int ord : chosen_orders) {
            int pu = ord;
            int dv = 1000 + ord;

            // try to relocate pickup
            {
                int idx_p = best_pu_pos[ord];
                int idx_d = best_dv_pos[ord];
                vector<int> old_tour = best_tour;
                vector<int> old_pu_pos = best_pu_pos;
                vector<int> old_dv_pos = best_dv_pos;

                // remove pickup
                best_tour.erase(best_tour.begin() + idx_p);
                for (int o : chosen_orders) {
                    if (best_pu_pos[o] > idx_p) --best_pu_pos[o];
                    if (best_dv_pos[o] > idx_p) --best_dv_pos[o];
                }
                int new_idx_d = best_dv_pos[ord];

                double L0 = compute_length(old_tour);
                double best_gain = 0;
                int best_new_idx = -1;
                int max_idx = min(new_idx_d, (int)best_tour.size() - 1);
                for (int new_idx = 1; new_idx <= max_idx; ++new_idx) {
                    vector<int> new_tour = best_tour;
                    new_tour.insert(new_tour.begin() + new_idx, pu);
                    double L1 = compute_length(new_tour);
                    double gain = L0 - L1;
                    if (gain > best_gain) {
                        best_gain = gain;
                        best_new_idx = new_idx;
                    }
                }
                if (best_gain > 0.5) {
                    best_tour.insert(best_tour.begin() + best_new_idx, pu);
                    for (int o : chosen_orders) {
                        if (best_pu_pos[o] >= best_new_idx) ++best_pu_pos[o];
                        if (best_dv_pos[o] >= best_new_idx) ++best_dv_pos[o];
                    }
                    best_pu_pos[ord] = best_new_idx;
                    improved = true;
                    break;
                } else {
                    best_tour = old_tour;
                    best_pu_pos = old_pu_pos;
                    best_dv_pos = old_dv_pos;
                }
            }

            if (improved) break;

            // try to relocate delivery
            {
                int idx_p = best_pu_pos[ord];
                int idx_d = best_dv_pos[ord];
                vector<int> old_tour = best_tour;
                vector<int> old_pu_pos = best_pu_pos;
                vector<int> old_dv_pos = best_dv_pos;

                // remove delivery
                best_tour.erase(best_tour.begin() + idx_d);
                for (int o : chosen_orders) {
                    if (best_pu_pos[o] > idx_d) --best_pu_pos[o];
                    if (best_dv_pos[o] > idx_d) --best_dv_pos[o];
                }
                int new_idx_p = best_pu_pos[ord];

                double L0 = compute_length(old_tour);
                double best_gain = 0;
                int best_new_idx = -1;
                int min_idx = max(1, new_idx_p + 1);
                for (int new_idx = min_idx; new_idx <= (int)best_tour.size() - 1; ++new_idx) {
                    vector<int> new_tour = best_tour;
                    new_tour.insert(new_tour.begin() + new_idx, dv);
                    double L1 = compute_length(new_tour);
                    double gain = L0 - L1;
                    if (gain > best_gain) {
                        best_gain = gain;
                        best_new_idx = new_idx;
                    }
                }
                if (best_gain > 0.5) {
                    best_tour.insert(best_tour.begin() + best_new_idx, dv);
                    for (int o : chosen_orders) {
                        if (best_pu_pos[o] >= best_new_idx) ++best_pu_pos[o];
                        if (best_dv_pos[o] >= best_new_idx) ++best_dv_pos[o];
                    }
                    best_dv_pos[ord] = best_new_idx;
                    improved = true;
                    break;
                } else {
                    best_tour = old_tour;
                    best_pu_pos = old_pu_pos;
                    best_dv_pos = old_dv_pos;
                }
            }

            if (improved) break;
        }
        if (!improved) break;
    }

    // output
    cout << 50;
    for (int ord : chosen_orders)
        cout << ' ' << ord + 1;
    cout << '\n';
    cout << best_tour.size();
    for (int idx : best_tour)
        cout << ' ' << px[idx] << ' ' << py[idx];
    cout << endl;

    return 0;
}