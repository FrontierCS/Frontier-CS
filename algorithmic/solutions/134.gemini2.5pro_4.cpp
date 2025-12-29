#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>
#include <tuple>

using namespace std;

typedef unsigned long long ull;
typedef __int128_t i128;

ull n;
ull la = 1, lb = 1;
vector<pair<ull, ull>> staircase;

mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

int ask(ull x, ull y) {
    cout << x << " " << y << endl;
    int resp;
    cin >> resp;
    if (resp == -1) exit(0); // In case of judge error
    return resp;
}

void add_to_staircase(ull x, ull y) {
    // Check if the new point is dominated by an existing one
    for (const auto& p : staircase) {
        if (p.first <= x && p.second <= y) {
            return;
        }
    }

    vector<pair<ull, ull>> new_staircase;
    new_staircase.push_back({x, y});

    // Remove existing points dominated by the new one
    for (const auto& p : staircase) {
        if (!(p.first >= x && p.second >= y)) {
            new_staircase.push_back(p);
        }
    }
    sort(new_staircase.begin(), new_staircase.end());
    staircase = new_staircase;
}

i128 uniform_i128(i128 high) {
    if (high == 0) return 0;
    i128 r1 = rng();
    i128 r2 = rng();
    i128 r = (r1 << 64) | r2;
    return r % high;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n;

    while (true) {
        vector<tuple<ull, ull, ull, ull>> rects;
        i128 total_area = 0;

        vector<pair<ull, ull>> current_stair = staircase;
        sort(current_stair.begin(), current_stair.end());
        
        ull p_prev = la - 1;
        // Decompose valid region into disjoint rectangles
        // Rect 1: from la to first p_i
        if (current_stair.empty() || current_stair.front().first > la) {
            ull rla = la;
            ull rra = current_stair.empty() ? n : current_stair.front().first - 1;
            ull rlb = lb;
            ull rrb = n;
            if (rra >= rla && rrb >= rlb) {
                rects.emplace_back(rla, rlb, rra, rrb);
                total_area += (i128)(rra - rla + 1) * (rrb - rlb + 1);
            }
        }
        
        // Rects between p_i's
        for (size_t i = 0; i < current_stair.size(); ++i) {
            ull pi = current_stair[i].first;
            ull qi = current_stair[i].second;

            ull rla = pi;
            ull rra = (i + 1 < current_stair.size()) ? current_stair[i+1].first - 1 : n;
            ull rlb = lb;
            ull rrb = qi - 1;

            if (rra >= rla && rrb >= rlb) {
                rects.emplace_back(rla, rlb, rra, rrb);
                total_area += (i128)(rra - rla + 1) * (rrb - rlb + 1);
            }
        }

        if (total_area <= 1) {
            if (total_area == 1) {
                 auto [rla, rlb, rra, rrb] = rects[0];
                 ask(rla, rlb);
            } else { // 0 area, must be single point [la,lb] which is invalid
                 ask(la, lb); // This case should ideally not be reached
            }
            return 0;
        }

        i128 rand_val = uniform_i128(total_area) + 1;
        
        ull x = 0, y = 0;
        i128 cumulative_area = 0;

        for (const auto& rect : rects) {
            auto [rla, rlb, rra, rrb] = rect;
            i128 area = (i128)(rra - rla + 1) * (rrb - rlb + 1);
            if (rand_val <= cumulative_area + area) {
                i128 offset = rand_val - cumulative_area - 1;
                ull width = rra - rla + 1;
                x = rla + (ull)(offset % width);
                y = rlb + (ull)(offset / width);
                break;
            }
            cumulative_area += area;
        }

        int resp = ask(x, y);

        if (resp == 0) {
            return 0;
        } else if (resp == 1) { // x < a
            la = max(la, x + 1);
        } else if (resp == 2) { // y < b
            lb = max(lb, y + 1);
        } else { // resp == 3, x > a or y > b
            add_to_staircase(x, y);
        }

        // Prune staircase points that are now out of bounds
        vector<pair<ull, ull>> next_staircase;
        for (const auto& p : staircase) {
            if (p.first >= la && p.second >= lb) {
                next_staircase.push_back(p);
            }
        }
        staircase = next_staircase;
    }

    return 0;
}