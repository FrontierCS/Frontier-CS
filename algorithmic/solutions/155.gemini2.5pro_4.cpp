#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <algorithm>
#include <cmath>

const int GRID_H = 20;
const int GRID_W = 20;

int si, sj, ti, tj;
double p;
std::vector<std::string> h_walls;
std::vector<std::string> v_walls;

int dist[GRID_H][GRID_W];
int dest[GRID_H][GRID_W][4]; // 0:U, 1:D, 2:L, 3:R

const char move_chars[] = "UDLR";

void compute_dist() {
    for (int i = 0; i < GRID_H; ++i) {
        for (int j = 0; j < GRID_W; ++j) {
            dist[i][j] = -1;
        }
    }

    std::queue<std::pair<int, int>> q;
    q.push({ti, tj});
    dist[ti][tj] = 0;

    while (!q.empty()) {
        auto [r, c] = q.front();
        q.pop();

        // Up
        if (r > 0 && v_walls[r - 1][c] == '0' && dist[r - 1][c] == -1) {
            dist[r - 1][c] = dist[r][c] + 1;
            q.push({r - 1, c});
        }
        // Down
        if (r < GRID_H - 1 && v_walls[r][c] == '0' && dist[r + 1][c] == -1) {
            dist[r + 1][c] = dist[r][c] + 1;
            q.push({r + 1, c});
        }
        // Left
        if (c > 0 && h_walls[r][c - 1] == '0' && dist[r][c - 1] == -1) {
            dist[r][c - 1] = dist[r][c] + 1;
            q.push({r, c - 1});
        }
        // Right
        if (c < GRID_W - 1 && h_walls[r][c] == '0' && dist[r][c + 1] == -1) {
            dist[r][c + 1] = dist[r][c] + 1;
            q.push({r, c + 1});
        }
    }
}

void precompute_dest() {
    for (int r = 0; r < GRID_H; ++r) {
        for (int c = 0; c < GRID_W; ++c) {
            // U
            if (r > 0 && v_walls[r - 1][c] == '0') dest[r][c][0] = (r - 1) * GRID_W + c;
            else dest[r][c][0] = r * GRID_W + c;
            // D
            if (r < GRID_H - 1 && v_walls[r][c] == '0') dest[r][c][1] = (r + 1) * GRID_W + c;
            else dest[r][c][1] = r * GRID_W + c;
            // L
            if (c > 0 && h_walls[r][c - 1] == '0') dest[r][c][2] = r * GRID_W + (c - 1);
            else dest[r][c][2] = r * GRID_W + c;
            // R
            if (c < GRID_W - 1 && h_walls[r][c] == '0') dest[r][c][3] = r * GRID_W + (c + 1);
            else dest[r][c][3] = r * GRID_W + c;
        }
    }
}

struct Beam {
    std::string path;
    std::vector<double> dp;
    double score;
    double heuristic_val;
};

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> si >> sj >> ti >> tj >> p;
    h_walls.resize(GRID_H);
    for (int i = 0; i < GRID_H; ++i) {
        std::cin >> h_walls[i];
    }
    v_walls.resize(GRID_H - 1);
    for (int i = 0; i < GRID_H - 1; ++i) {
        std::cin >> v_walls[i];
    }

    compute_dist();
    precompute_dest();

    const int BEAM_WIDTH = 20;
    const int MAX_LEN = 200;

    std::vector<Beam> beams;
    beams.reserve(BEAM_WIDTH);
    Beam initial_beam;
    initial_beam.path = "";
    initial_beam.dp.assign(GRID_H * GRID_W, 0.0);
    initial_beam.dp[si * GRID_W + sj] = 1.0;
    initial_beam.score = 0.0;
    beams.push_back(initial_beam);

    for (int k = 1; k <= MAX_LEN; ++k) {
        std::vector<Beam> candidates;
        candidates.reserve(beams.size() * 4);
        for (const auto& beam : beams) {
            for (int move_idx = 0; move_idx < 4; ++move_idx) {
                Beam next_beam;
                next_beam.path = beam.path + move_chars[move_idx];
                next_beam.dp.assign(GRID_H * GRID_W, 0.0);

                double prob_reach_this_turn = 0.0;
                
                for (int r = 0; r < GRID_H; ++r) {
                    for (int c = 0; c < GRID_W; ++c) {
                        int pos = r * GRID_W + c;
                        double current_prob = beam.dp[pos];
                        if (current_prob == 0.0) continue;

                        next_beam.dp[pos] += current_prob * p;

                        int next_pos = dest[r][c][move_idx];
                        if (next_pos == ti * GRID_W + tj) {
                            prob_reach_this_turn += current_prob * (1.0 - p);
                        } else {
                            next_beam.dp[next_pos] += current_prob * (1.0 - p);
                        }
                    }
                }

                next_beam.score = beam.score + (401.0 - k) * prob_reach_this_turn;

                double expected_dist = 0.0;
                for (int i = 0; i < GRID_H * GRID_W; ++i) {
                    expected_dist += next_beam.dp[i] * dist[i / GRID_W][i % GRID_W];
                }
                next_beam.heuristic_val = expected_dist;
                candidates.push_back(std::move(next_beam));
            }
        }
        
        std::sort(candidates.begin(), candidates.end(), [](const Beam& a, const Beam& b) {
            if (std::abs(a.heuristic_val - b.heuristic_val) > 1e-9) {
                return a.heuristic_val < b.heuristic_val;
            }
            return a.score > b.score;
        });

        beams.clear();
        for (int i = 0; i < std::min((int)candidates.size(), BEAM_WIDTH); ++i) {
            beams.push_back(std::move(candidates[i]));
        }
    }

    Beam* best_beam = &beams[0];
    for (size_t i = 1; i < beams.size(); ++i) {
        if (beams[i].score > best_beam->score) {
            best_beam = &beams[i];
        }
    }

    std::cout << best_beam->path << std::endl;

    return 0;
}