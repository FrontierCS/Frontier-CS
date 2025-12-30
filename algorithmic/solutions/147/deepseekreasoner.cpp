#include <bits/stdc++.h>
using namespace std;

using ll = long long;

int n;
vector<int> x, y;
vector<ll> r;
vector<int> a, b, c, d;
vector<ll> s;
vector<double> p;

mt19937 rng;

double satisfaction(ll s, ll r) {
    if (s == 0) return 0.0;
    double ratio = (double) min(s, r) / max(s, r);
    return 1.0 - (1.0 - ratio) * (1.0 - ratio);
}

bool overlaps(int a1, int c1, int b1, int d1, int a2, int c2, int b2, int d2) {
    return max(a1, a2) < min(c1, c2) && max(b1, b2) < min(d1, d2);
}

void compute_limits(int i, int& left_limit, int& right_limit, int& bottom_limit, int& top_limit) {
    left_limit = 0;
    right_limit = 10000;
    bottom_limit = 0;
    top_limit = 10000;
    for (int j = 0; j < n; ++j) {
        if (j == i) continue;
        // y-overlap
        if (max(b[i], b[j]) < min(d[i], d[j])) {
            if (c[j] <= a[i]) left_limit = max(left_limit, c[j]);
            if (a[j] >= c[i]) right_limit = min(right_limit, a[j]);
        }
        // x-overlap
        if (max(a[i], a[j]) < min(c[i], c[j])) {
            if (d[j] <= b[i]) bottom_limit = max(bottom_limit, d[j]);
            if (b[j] >= d[i]) top_limit = min(top_limit, b[j]);
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Seed random
    rng.seed(chrono::steady_clock::now().time_since_epoch().count());

    // Read input
    cin >> n;
    x.resize(n);
    y.resize(n);
    r.resize(n);
    for (int i = 0; i < n; ++i) {
        cin >> x[i] >> y[i] >> r[i];
    }

    // Initialize rectangles as unit cells containing the point
    a.assign(n, 0);
    b.assign(n, 0);
    c.assign(n, 0);
    d.assign(n, 0);
    s.assign(n, 0);
    p.assign(n, 0.0);
    for (int i = 0; i < n; ++i) {
        a[i] = x[i];
        b[i] = y[i];
        c[i] = x[i] + 1;
        d[i] = y[i] + 1;
        s[i] = 1;
        p[i] = satisfaction(s[i], r[i]);
    }

    // Simulated Annealing
    const int MAX_ITER = 200000;
    const int STEP = 100;
    const double start_temp = 1.0;
    const double end_temp = 1e-9;

    uniform_real_distribution<> uniform(0.0, 1.0);
    uniform_int_distribution<> rand_idx(0, n-1);
    uniform_int_distribution<> rand_side(0, 3);
    uniform_int_distribution<> rand_delta(-STEP, STEP);

    for (int iter = 0; iter < MAX_ITER; ++iter) {
        int i = rand_idx(rng);
        int side = rand_side(rng);
        int cur, minv, maxv;
        if (side == 0) {
            cur = a[i];
            minv = 0;
            maxv = x[i];
        } else if (side == 1) {
            cur = c[i];
            minv = x[i] + 1;
            maxv = 10000;
        } else if (side == 2) {
            cur = b[i];
            minv = 0;
            maxv = y[i];
        } else {
            cur = d[i];
            minv = y[i] + 1;
            maxv = 10000;
        }

        int delta = rand_delta(rng);
        if (delta == 0) delta = (uniform(rng) < 0.5) ? 1 : -1;
        int new_val = cur + delta;
        if (new_val < minv) new_val = minv;
        if (new_val > maxv) new_val = maxv;
        if (new_val == cur) continue;

        int new_a = a[i], new_b = b[i], new_c = c[i], new_d = d[i];
        if (side == 0) new_a = new_val;
        else if (side == 1) new_c = new_val;
        else if (side == 2) new_b = new_val;
        else new_d = new_val;

        // Check overlap
        bool overlap = false;
        for (int j = 0; j < n; ++j) {
            if (j == i) continue;
            if (overlaps(new_a, new_c, new_b, new_d, a[j], c[j], b[j], d[j])) {
                overlap = true;
                break;
            }
        }
        if (overlap) continue;

        // Compute satisfaction change
        ll new_area = (ll)(new_c - new_a) * (new_d - new_b);
        ll old_area = s[i];
        double old_p = p[i];
        double new_p = satisfaction(new_area, r[i]);
        double delta_score = new_p - old_p;

        double temp = start_temp * pow(end_temp/start_temp, (double)iter/MAX_ITER);
        if (delta_score >= 0 || exp(delta_score / temp) > uniform(rng)) {
            // Accept move
            a[i] = new_a;
            b[i] = new_b;
            c[i] = new_c;
            d[i] = new_d;
            s[i] = new_area;
            p[i] = new_p;
        }
    }

    // Greedy refinement
    const int MAX_PASS = 10;
    for (int pass = 0; pass < MAX_PASS; ++pass) {
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);

        bool improved = false;
        for (int i : order) {
            // Compute limits for each side
            int left_limit, right_limit, bottom_limit, top_limit;
            compute_limits(i, left_limit, right_limit, bottom_limit, top_limit);

            // Try left boundary
            if (left_limit <= a[i]) {
                int height = d[i] - b[i];
                auto eval = [&](int na) -> double {
                    ll new_area = (ll)(c[i] - na) * height;
                    return satisfaction(new_area, r[i]);
                };
                double best_p = p[i];
                int best_a = a[i];
                // Candidate values: left_limit, current, and the one that gives area closest to r_i
                int cand1 = left_limit;
                double p1 = eval(cand1);
                if (p1 > best_p) {
                    best_p = p1;
                    best_a = cand1;
                }
                // Compute ideal a to get area = r_i
                if (height > 0) {
                    double a_exact = c[i] - (double)r[i] / height;
                    for (int offset = -1; offset <= 1; ++offset) {
                        int cand = round(a_exact) + offset;
                        if (cand >= left_limit && cand <= a[i]) {
                            double pc = eval(cand);
                            if (pc > best_p) {
                                best_p = pc;
                                best_a = cand;
                            }
                        }
                    }
                }
                if (best_a != a[i]) {
                    a[i] = best_a;
                    s[i] = (ll)(c[i] - a[i]) * (d[i] - b[i]);
                    p[i] = best_p;
                    improved = true;
                    continue; // move to next rectangle after one change
                }
            }

            // Try right boundary
            if (c[i] <= right_limit) {
                int height = d[i] - b[i];
                auto eval = [&](int nc) -> double {
                    ll new_area = (ll)(nc - a[i]) * height;
                    return satisfaction(new_area, r[i]);
                };
                double best_p = p[i];
                int best_c = c[i];
                int cand1 = right_limit;
                double p1 = eval(cand1);
                if (p1 > best_p) {
                    best_p = p1;
                    best_c = cand1;
                }
                if (height > 0) {
                    double c_exact = a[i] + (double)r[i] / height;
                    for (int offset = -1; offset <= 1; ++offset) {
                        int cand = round(c_exact) + offset;
                        if (cand >= c[i] && cand <= right_limit) {
                            double pc = eval(cand);
                            if (pc > best_p) {
                                best_p = pc;
                                best_c = cand;
                            }
                        }
                    }
                }
                if (best_c != c[i]) {
                    c[i] = best_c;
                    s[i] = (ll)(c[i] - a[i]) * (d[i] - b[i]);
                    p[i] = best_p;
                    improved = true;
                    continue;
                }
            }

            // Try bottom boundary
            if (bottom_limit <= b[i]) {
                int width = c[i] - a[i];
                auto eval = [&](int nb) -> double {
                    ll new_area = (ll)width * (d[i] - nb);
                    return satisfaction(new_area, r[i]);
                };
                double best_p = p[i];
                int best_b = b[i];
                int cand1 = bottom_limit;
                double p1 = eval(cand1);
                if (p1 > best_p) {
                    best_p = p1;
                    best_b = cand1;
                }
                if (width > 0) {
                    double b_exact = d[i] - (double)r[i] / width;
                    for (int offset = -1; offset <= 1; ++offset) {
                        int cand = round(b_exact) + offset;
                        if (cand >= bottom_limit && cand <= b[i]) {
                            double pc = eval(cand);
                            if (pc > best_p) {
                                best_p = pc;
                                best_b = cand;
                            }
                        }
                    }
                }
                if (best_b != b[i]) {
                    b[i] = best_b;
                    s[i] = (ll)(c[i] - a[i]) * (d[i] - b[i]);
                    p[i] = best_p;
                    improved = true;
                    continue;
                }
            }

            // Try top boundary
            if (d[i] <= top_limit) {
                int width = c[i] - a[i];
                auto eval = [&](int nd) -> double {
                    ll new_area = (ll)width * (nd - b[i]);
                    return satisfaction(new_area, r[i]);
                };
                double best_p = p[i];
                int best_d = d[i];
                int cand1 = top_limit;
                double p1 = eval(cand1);
                if (p1 > best_p) {
                    best_p = p1;
                    best_d = cand1;
                }
                if (width > 0) {
                    double d_exact = b[i] + (double)r[i] / width;
                    for (int offset = -1; offset <= 1; ++offset) {
                        int cand = round(d_exact) + offset;
                        if (cand >= d[i] && cand <= top_limit) {
                            double pc = eval(cand);
                            if (pc > best_p) {
                                best_p = pc;
                                best_d = cand;
                            }
                        }
                    }
                }
                if (best_d != d[i]) {
                    d[i] = best_d;
                    s[i] = (ll)(c[i] - a[i]) * (d[i] - b[i]);
                    p[i] = best_p;
                    improved = true;
                    continue;
                }
            }
        }
        if (!improved) break;
    }

    // Output
    for (int i = 0; i < n; ++i) {
        cout << a[i] << " " << b[i] << " " << c[i] << " " << d[i] << "\n";
    }

    return 0;
}