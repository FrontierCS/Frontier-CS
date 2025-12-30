#include <bits/stdc++.h>
using namespace std;

const int CENTER = 0;
const int MAX_ORDERS = 1000;
const int SELECT = 50;
const int INF = 1e9;

struct Point {
    int x, y;
    Point() {}
    Point(int x, int y) : x(x), y(y) {}
};

int manhattan(const Point& a, const Point& b) {
    return abs(a.x - b.x) + abs(a.y - b.y);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read orders
    vector<Point> pickup(MAX_ORDERS + 1);   // index 1..1000
    vector<Point> delivery(MAX_ORDERS + 1); // index 1..1000
    for (int i = 1; i <= MAX_ORDERS; i++) {
        int a, b, c, d;
        cin >> a >> b >> c >> d;
        pickup[i] = Point(a, b);
        delivery[i] = Point(c, d);
    }

    // Prepare points: 0: center, 1..1000: pickups, 1001..2000: deliveries
    vector<Point> pt(1 + MAX_ORDERS + MAX_ORDERS);
    pt[CENTER] = Point(400, 400);
    for (int i = 1; i <= MAX_ORDERS; i++) {
        pt[i] = pickup[i];
        pt[i + MAX_ORDERS] = delivery[i];
    }
    int total_pts = pt.size();

    // Precompute distance matrix
    vector<vector<int>> dist(total_pts, vector<int>(total_pts));
    for (int i = 0; i < total_pts; i++) {
        for (int j = 0; j < total_pts; j++) {
            dist[i][j] = manhattan(pt[i], pt[j]);
        }
    }

    // Greedy insertion
    vector<bool> used(MAX_ORDERS + 1, false);
    vector<int> chosen;               // order ids
    vector<int> tour = {CENTER, CENTER}; // start and end at center
    long long total_dist = 0;

    // Helper to compute insertion cost for an order given current tour
    auto compute_best = [&](int order, int& best_i, int& best_j) -> long long {
        int p = order;
        int d = order + MAX_ORDERS;
        int L = tour.size();
        int edges = L - 1;
        vector<long long> edge_len(edges);
        for (int k = 0; k < edges; k++) {
            edge_len[k] = dist[tour[k]][tour[k+1]];
        }

        vector<long long> A(edges), B(edges), C(edges);
        for (int i = 0; i < edges; i++) {
            A[i] = dist[tour[i]][p] + dist[p][tour[i+1]] - edge_len[i];
            B[i] = dist[tour[i]][d] + dist[d][tour[i+1]] - edge_len[i];
            C[i] = dist[tour[i]][p] + dist[p][d] + dist[d][tour[i+1]] - edge_len[i];
        }

        // suffix minima for B
        vector<long long> suf_min(edges + 1, INF);
        vector<int> suf_idx(edges + 1, -1);
        for (int i = edges-1; i >= 0; i--) {
            suf_min[i] = B[i];
            suf_idx[i] = i;
            if (i+1 < edges && suf_min[i+1] < suf_min[i]) {
                suf_min[i] = suf_min[i+1];
                suf_idx[i] = suf_idx[i+1];
            }
        }

        long long best_delta = INF;
        best_i = best_j = -1;
        for (int i = 0; i < edges; i++) {
            // case i == j
            if (C[i] < best_delta) {
                best_delta = C[i];
                best_i = i;
                best_j = i;
            }
            // case i < j
            if (i+1 < edges) {
                long long cand = A[i] + suf_min[i+1];
                if (cand < best_delta) {
                    best_delta = cand;
                    best_i = i;
                    best_j = suf_idx[i+1];
                }
            }
        }
        return best_delta;
    };

    // First order: choose the one with smallest individual tour cost
    long long best_first = INF;
    int first_order = -1;
    for (int o = 1; o <= MAX_ORDERS; o++) {
        int p = o;
        int d = o + MAX_ORDERS;
        long long cost = dist[CENTER][p] + dist[p][d] + dist[d][CENTER];
        if (cost < best_first) {
            best_first = cost;
            first_order = o;
        }
    }
    chosen.push_back(first_order);
    used[first_order] = true;
    int p1 = first_order;
    int d1 = first_order + MAX_ORDERS;
    tour.insert(tour.begin() + 1, p1);
    tour.insert(tour.begin() + 2, d1);
    total_dist = best_first;

    // Insert remaining 49 orders
    for (int step = 2; step <= SELECT; step++) {
        long long best_delta = INF;
        int best_order = -1;
        int best_i = -1, best_j = -1;
        for (int o = 1; o <= MAX_ORDERS; o++) {
            if (used[o]) continue;
            int i, j;
            long long delta = compute_best(o, i, j);
            if (delta < best_delta) {
                best_delta = delta;
                best_order = o;
                best_i = i;
                best_j = j;
            }
        }
        // Insert best_order
        chosen.push_back(best_order);
        used[best_order] = true;
        int p = best_order;
        int d = best_order + MAX_ORDERS;
        // Insert p at position best_i+1
        tour.insert(tour.begin() + best_i + 1, p);
        // Insert d: if best_i == best_j, insert at best_i+2; else at best_j+2
        if (best_i == best_j) {
            tour.insert(tour.begin() + best_i + 2, d);
        } else {
            // after inserting p, best_j increased by 1
            tour.insert(tour.begin() + best_j + 2, d);
        }
        total_dist += best_delta;
    }

    // Local improvement: relocate pickups and deliveries
    auto relocate_pickup = [&](int order) -> bool {
        int p = order;
        int d = order + MAX_ORDERS;
        int pos_p = -1, pos_d = -1;
        int L = tour.size();
        for (int i = 0; i < L; i++) {
            if (tour[i] == p) pos_p = i;
            if (tour[i] == d) pos_d = i;
        }
        if (pos_p == 0 || pos_p == L-1 || pos_d == 0 || pos_d == L-1) return false;
        // removal delta
        long long rem_delta = -dist[tour[pos_p-1]][p] - dist[p][tour[pos_p+1]] + dist[tour[pos_p-1]][tour[pos_p+1]];
        int new_pos_d = (pos_d > pos_p) ? pos_d-1 : pos_d;
        long long best_delta = 0;
        int best_k = -1;
        for (int k = 1; k <= L-2; k++) {
            if (k == pos_p) continue;
            if (k > new_pos_d) break;
            int left, right;
            if (k < pos_p) {
                left = tour[k-1];
                right = tour[k];
            } else if (k == pos_p) {
                left = tour[k-1];
                right = tour[k+1];
            } else { // k > pos_p
                left = tour[k];
                right = tour[k+1];
            }
            long long ins_delta = dist[left][p] + dist[p][right] - dist[left][right];
            long long delta = rem_delta + ins_delta;
            if (delta < best_delta) {
                best_delta = delta;
                best_k = k;
            }
        }
        if (best_k != -1) {
            tour.erase(tour.begin() + pos_p);
            tour.insert(tour.begin() + best_k, p);
            total_dist += best_delta;
            return true;
        }
        return false;
    };

    auto relocate_delivery = [&](int order) -> bool {
        int d = order + MAX_ORDERS;
        int p = order;
        int pos_d = -1, pos_p = -1;
        int L = tour.size();
        for (int i = 0; i < L; i++) {
            if (tour[i] == d) pos_d = i;
            if (tour[i] == p) pos_p = i;
        }
        if (pos_d == 0 || pos_d == L-1 || pos_p == 0 || pos_p == L-1) return false;
        long long rem_delta = -dist[tour[pos_d-1]][d] - dist[d][tour[pos_d+1]] + dist[tour[pos_d-1]][tour[pos_d+1]];
        int new_pos_p = pos_p; // since pos_p < pos_d
        long long best_delta = 0;
        int best_k = -1;
        int start_k = max(new_pos_p + 1, 1);
        for (int k = start_k; k <= L-2; k++) {
            if (k == pos_d) continue;
            int left, right;
            if (k < pos_d) {
                left = tour[k-1];
                right = tour[k];
            } else if (k == pos_d) {
                left = tour[k-1];
                right = tour[k+1];
            } else { // k > pos_d
                left = tour[k];
                right = tour[k+1];
            }
            long long ins_delta = dist[left][d] + dist[d][right] - dist[left][right];
            long long delta = rem_delta + ins_delta;
            if (delta < best_delta) {
                best_delta = delta;
                best_k = k;
            }
        }
        if (best_k != -1) {
            tour.erase(tour.begin() + pos_d);
            tour.insert(tour.begin() + best_k, d);
            total_dist += best_delta;
            return true;
        }
        return false;
    };

    bool improved = true;
    while (improved) {
        improved = false;
        for (int o : chosen) {
            if (relocate_pickup(o)) improved = true;
            if (relocate_delivery(o)) improved = true;
        }
    }

    // Output
    sort(chosen.begin(), chosen.end());
    cout << SELECT;
    for (int o : chosen) cout << " " << o;
    cout << "\n";
    cout << tour.size();
    for (int idx : tour) {
        if (idx == CENTER) {
            cout << " 400 400";
        } else if (idx <= MAX_ORDERS) {
            cout << " " << pt[idx].x << " " << pt[idx].y;
        } else {
            cout << " " << pt[idx].x << " " << pt[idx].y;
        }
    }
    cout << endl;

    return 0;
}