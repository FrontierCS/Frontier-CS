#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <limits>

using namespace std;

const int N = 20;
int h[N][N];
int cr, cc;
long long load;
vector<string> ops;

struct Pos {
    int r, c;
};

void move_to(int r, int c) {
    while (cr < r) {
        ops.push_back("D");
        cr++;
    }
    while (cr > r) {
        ops.push_back("U");
        cr--;
    }
    while (cc < c) {
        ops.push_back("R");
        cc++;
    }
    while (cc > c) {
        ops.push_back("L");
        cc--;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n_dummy;
    cin >> n_dummy;

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cin >> h[i][j];
        }
    }

    cr = 0;
    cc = 0;
    load = 0;

    while (true) {
        vector<Pos> sources;
        vector<Pos> sinks;
        
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                if (h[i][j] > 0) {
                    sources.push_back({i, j});
                } else if (h[i][j] < 0) {
                    sinks.push_back({i, j});
                }
            }
        }

        if (sources.empty()) {
            break;
        }
        
        if (load == 0) {
            Pos best_s = {-1, -1}, best_k = {-1, -1};
            long long min_cost = numeric_limits<long long>::max();

            for (const auto& s : sources) {
                for (const auto& k : sinks) {
                    long long dist_to_s = abs(cr - s.r) + abs(cc - s.c);
                    long long dist_s_to_k = abs(s.r - k.r) + abs(s.c - k.c);
                    long long current_cost = dist_to_s * 100LL + dist_s_to_k * (100LL + h[s.r][s.c]);

                    if (current_cost < min_cost) {
                        min_cost = current_cost;
                        best_s = s;
                        best_k = k;
                    } else if (current_cost == min_cost) {
                        if (best_s.r == -1 || h[s.r][s.c] > h[best_s.r][best_s.c]) {
                            best_s = s;
                            best_k = k;
                        }
                    }
                }
            }
            
            if (best_s.r == -1) {
                break;
            }

            move_to(best_s.r, best_s.c);
            
            int amount_to_load = h[best_s.r][best_s.c];
            if (amount_to_load > 0) {
                ops.push_back("+" + to_string(amount_to_load));
                load += amount_to_load;
                h[best_s.r][best_s.c] = 0;
            }

            move_to(best_k.r, best_k.c);

            int amount_to_unload = min((long long)-h[best_k.r][best_k.c], load);
            if (amount_to_unload > 0) {
                ops.push_back("-" + to_string(amount_to_unload));
                load -= amount_to_unload;
                h[best_k.r][best_k.c] += amount_to_unload;
            }
        }
        
        while (load > 0) {
            sinks.clear();
            for (int i = 0; i < N; ++i) {
                for (int j = 0; j < N; ++j) {
                    if (h[i][j] < 0) {
                        sinks.push_back({i, j});
                    }
                }
            }

            if (sinks.empty()) {
                 break;
            }

            Pos closest_k = {-1, -1};
            int min_dist = numeric_limits<int>::max();

            for (const auto& k : sinks) {
                int d = abs(cr - k.r) + abs(cc - k.c);
                if (d < min_dist) {
                    min_dist = d;
                    closest_k = k;
                }
            }

            if (closest_k.r == -1) {
                break;
            }

            move_to(closest_k.r, closest_k.c);
            
            int amount_to_unload = min((long long)-h[closest_k.r][closest_k.c], load);
            if (amount_to_unload > 0) {
                ops.push_back("-" + to_string(amount_to_unload));
                load -= amount_to_unload;
                h[closest_k.r][closest_k.c] += amount_to_unload;
            }
        }
    }

    for (const auto& op : ops) {
        cout << op << "\n";
    }

    return 0;
}