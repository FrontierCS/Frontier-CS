#include <cmath>
#include <algorithm>

// Natural-log calibration above the previous 60-point threshold.
// Keep validation and low scores; an exact zero minimization cost earns 100.
static double natural_log_score(double old_points, long double value,
                                long double anchor, bool minimize) {
    if (minimize && value == 0.0L) return 100.0;
    if (old_points <= 60.0 || !(value > 0.0L) || !(anchor > 0.0L))
        return old_points;
    const long double delta = minimize ? std::log(anchor) - std::log(value)
                                       : std::log(value) - std::log(anchor);
    return (double)std::min(100.0L, 60.0L + delta);
}

#include <bits/stdc++.h>
#include "testlib.h"
using namespace std;
using ll = long long;
using pii = pair<int, int>;

const int BOARD_SIZE = 6;
const int RED_CAR_ID = 1;
const int EXIT_ROW = 3;

typedef enum _Dir {
    horizon = 0,
    vertical,
} Dir;

class Vehicle {
public:
    Dir dir;
    vector<pii> locs;
};

vector<vector<int>> board(BOARD_SIZE + 1, vector<int>(BOARD_SIZE + 1));
map<int, Vehicle> vehicle_map;

int solvePuzzle() {
    // Keep vehicle identities in the state. The occupied-cell bitmap alone
    // cannot distinguish different placements of adjacent vehicles.
    struct Spec { int length; bool horizontal; unsigned long long masks[6]{}; };
    vector<Spec> specs;
    unsigned long long initial = 0;
    for (const auto& entry : vehicle_map) {
        const auto& vehicle = entry.second;
        Spec spec;
        spec.length = (int)vehicle.locs.size();
        spec.horizontal = vehicle.dir == horizon;
        int fixed = (spec.horizontal ? vehicle.locs[0].first : vehicle.locs[0].second) - 1;
        int position = (spec.horizontal ? vehicle.locs[0].second : vehicle.locs[0].first) - 1;
        ensuref(spec.length >= 2 && spec.length <= 3, "Invalid vehicle length");
        for (int pos = 0; pos + spec.length <= 6; ++pos) {
            for (int offset = 0; offset < spec.length; ++offset) {
                int row = spec.horizontal ? fixed : pos + offset;
                int col = spec.horizontal ? pos + offset : fixed;
                spec.masks[pos] |= 1ULL << (row * 6 + col);
            }
        }
        initial |= (unsigned long long)position << (3 * specs.size());
        specs.push_back(spec);
    }
    ensuref(!specs.empty() && vehicle_map.begin()->first == 1 && specs.size() <= 18,
            "Invalid vehicle layout");
    unordered_set<unsigned long long> seen;
    seen.reserve(1 << 18);
    vector<pair<unsigned long long, int>> queue;
    queue.emplace_back(initial, 0);
    seen.insert(initial);
    for (size_t head = 0; head < queue.size(); ++head) {
        auto [state, steps] = queue[head];
        if (int(state & 7) + specs[0].length == 6) return steps + 2;
        unsigned long long occupied = 0;
        int positions[18];
        for (size_t i = 0; i < specs.size(); ++i) {
            positions[i] = (state >> (3 * i)) & 7;
            occupied |= specs[i].masks[positions[i]];
        }
        for (size_t i = 0; i < specs.size(); ++i) {
            int pos = positions[i];
            for (int delta : {-1, 1}) {
                int next = pos + delta;
                if (next < 0 || next + specs[i].length > 6) continue;
                if ((specs[i].masks[next] & ~specs[i].masks[pos]) & occupied) continue;
                auto successor = (state & ~(7ULL << (3 * i))) |
                                 ((unsigned long long)next << (3 * i));
                if (seen.insert(successor).second) queue.emplace_back(successor, steps + 1);
            }
        }
    }
    return -1;
}

void parseBoard() {
    vehicle_map.clear();
    for (int i = 1; i <= BOARD_SIZE; i++) {
        for (int j = 1; j <= BOARD_SIZE; j++) {
            int id = board[i][j];
            if (id > 0) {
                if (vehicle_map.find(id) == vehicle_map.end()) {
                    vehicle_map[id].dir = horizon;
                }
                vehicle_map[id].locs.push_back({i, j});
            }
        }
    }

    for (auto& p : vehicle_map) {
        Vehicle& v = p.second;
        sort(v.locs.begin(), v.locs.end());
        if (v.locs.size() >= 2) {
            if (v.locs[0].first == v.locs[1].first) {
                v.dir = horizon;
            } else {
                v.dir = vertical;
            }
        }
    }
}

bool isValidMove(int vehicle_id, char direction) {
    if (vehicle_map.find(vehicle_id) == vehicle_map.end()) {
        return false;
    }

    Vehicle& v = vehicle_map[vehicle_id];

    if (v.dir == horizon && (direction != 'L' && direction != 'R')) {
        return false;
    }
    if (v.dir == vertical && (direction != 'U' && direction != 'D')) {
        return false;
    }

    vector<pair<int, int>> new_positions = v.locs;
    for (auto& pos : new_positions) {
        if (direction == 'U') pos.first--;
        else if (direction == 'D') pos.first++;
        else if (direction == 'L') pos.second--;
        else if (direction == 'R') pos.second++;
    }

    for (auto& pos : new_positions) {
        if (pos.first < 1 || pos.first > BOARD_SIZE ||
            pos.second < 1 || pos.second > BOARD_SIZE) {
            return false;
        }
    }

    for (auto& pos : new_positions) {
        int occupant = board[pos.first][pos.second];
        if (occupant != 0 && occupant != vehicle_id) {
            return false;
        }
    }

    return true;
}

void applyMove(int vehicle_id, char direction) {
    Vehicle& v = vehicle_map[vehicle_id];

    for (auto& pos : v.locs) {
        board[pos.first][pos.second] = 0;
    }

    for (auto& pos : v.locs) {
        if (direction == 'U') pos.first--;
        else if (direction == 'D') pos.first++;
        else if (direction == 'L') pos.second--;
        else if (direction == 'R') pos.second++;
    }

    for (auto& pos : v.locs) {
        board[pos.first][pos.second] = vehicle_id;
    }
}

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    for (int i = 1; i <= BOARD_SIZE; i++) {
        for (int j = 1; j <= BOARD_SIZE; j++) {
            board[i][j] = inf.readInt();
        }
    }

    parseBoard();

    int ref_min_steps = ans.readInt();
    int ref_num_moves = ans.readInt();

    if (ouf.seekEof()) {
        quitf(_wa, "No output provided");
    }

    int participant_min_steps = ouf.readInt();
    int participant_num_moves = ouf.readInt();

    if (participant_min_steps < 0) {
        quitf(_wa, "Minimum steps cannot be negative: %d", participant_min_steps);
    }

    if (participant_num_moves < 0) {
        quitf(_wa, "Number of formation moves cannot be negative: %d", participant_num_moves);
    }

    vector<pair<int, char>> moves;
    for (int i = 0; i < participant_num_moves; i++) {
        if (ouf.seekEof()) {
            quitf(_wa, "Expected %d formation moves, but only found %d", participant_num_moves, i);
        }

        int vehicle_id = ouf.readInt();
        string dir_str = ouf.readToken();

        if (dir_str.length() != 1) {
            quitf(_wa, "Invalid direction at move %d: %s", i + 1, dir_str.c_str());
        }

        char direction = dir_str[0];
        if (direction != 'U' && direction != 'D' && direction != 'L' && direction != 'R') {
            quitf(_wa, "Invalid direction at move %d: %c", i + 1, direction);
        }

        moves.push_back({vehicle_id, direction});
    }

    if (!ouf.seekEof()) {
        quitf(_wa, "Extra output found after %d formation moves", participant_num_moves);
    }

    for (int i = 0; i < participant_num_moves; i++) {
        int vehicle_id = moves[i].first;
        char direction = moves[i].second;

        if (!isValidMove(vehicle_id, direction)) {
            quitf(_wa, "Invalid formation move %d: vehicle %d direction %c",
                  i + 1, vehicle_id, direction);
        }

        applyMove(vehicle_id, direction);
    }

    parseBoard();

    int actual_min_steps = solvePuzzle();

    if (actual_min_steps < 0) {
        quitf(_wa, "The formed puzzle is not solvable");
    }

    if (actual_min_steps != participant_min_steps) {
        quitf(_wa, "Claimed minimum steps %d does not match actual %d",
              participant_min_steps, actual_min_steps);
    }

    if (ref_min_steps < 0) quitf(_fail, "Negative reference minimum steps");
    double performance = (double(participant_min_steps) + 1.0) / (double(ref_min_steps) + 1.0);
    double score_ratio = (performance <= 1.0 ? 0.6 * performance : 0.6 + 0.01 * log(performance));
    score_ratio = natural_log_score(100.0 * score_ratio, participant_min_steps, ref_min_steps, false) / 100.0;
    double unbounded_ratio = score_ratio;

    quitp(score_ratio, "New puzzle min steps: %d (ref: %d). Ratio: %.12f, RatioUnbounded: %.12f",
          participant_min_steps, ref_min_steps, score_ratio, unbounded_ratio);

    return 0;
}
