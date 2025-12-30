#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <set>
#include <algorithm>
#include <map>

using namespace std;

int N, M;
vector<pair<int, int>> targets;
vector<vector<bool>> blocks;
int cur_i, cur_j;
vector<pair<char, char>> actions;

const double ALPHA = 0.4;

struct Point {
    int r, c;
};

int manhattan_distance(int r1, int c1, int r2, int c2) {
    return abs(r1 - r2) + abs(c1 - c2);
}

bool is_valid(int r, int c) {
    return r >= 0 && r < N && c >= 0 && c < N;
}

bool is_path_clear(int r1, int c1, int r2, int c2, bool vertical_first, const vector<vector<bool>>& current_blocks) {
    if (vertical_first) {
        if (r1 != r2) {
            int r_start = min(r1, r2), r_end = max(r1, r2);
            for (int r = r_start; r <= r_end; ++r) {
                if (r == r1) continue;
                if (current_blocks[r][c1]) return false;
            }
        }
        if (c1 != c2) {
            int c_start = min(c1, c2), c_end = max(c1, c2);
            for (int c = c_start; c <= c_end; ++c) {
                if (c == c1) continue;
                if (current_blocks[r2][c]) return false;
            }
        }
    } else {
        if (c1 != c2) {
            int c_start = min(c1, c2), c_end = max(c1, c2);
            for (int c = c_start; c <= c_end; ++c) {
                if (c == c1) continue;
                if (current_blocks[r1][c]) return false;
            }
        }
        if (r1 != r2) {
            int r_start = min(r1, r2), r_end = max(r1, r2);
            for (int r = r_start; r <= r_end; ++r) {
                if (r == r1) continue;
                if (current_blocks[r][c2]) return false;
            }
        }
    }
    return true;
}


Point get_slide_destination(int r, int c, char dir, const vector<vector<bool>>& current_blocks) {
    if (dir == 'U') {
        int nr = r - 1;
        while (nr >= 0 && !current_blocks[nr][c]) nr--;
        return {nr + 1, c};
    }
    if (dir == 'D') {
        int nr = r + 1;
        while (nr < N && !current_blocks[nr][c]) nr++;
        return {nr - 1, c};
    }
    if (dir == 'L') {
        int nc = c - 1;
        while (nc >= 0 && !current_blocks[r][nc]) nc--;
        return {r, nc + 1};
    }
    if (dir == 'R') {
        int nc = c + 1;
        while (nc < N && !current_blocks[r][nc]) nc++;
        return {r, nc - 1};
    }
    return {-1, -1};
}

void apply_move(int r1, int c1, int r2, int c2, bool vertical_first) {
    int dr = (r1 < r2) ? 1 : -1;
    int dc = (c1 < c2) ? 1 : -1;
    if (vertical_first) {
        for (int r = r1; r != r2; r += dr) actions.push_back({'M', (dr > 0 ? 'D' : 'U')});
        for (int c = c1; c != c2; c += dc) actions.push_back({'M', (dc > 0 ? 'R' : 'L')});
    } else {
        for (int c = c1; c != c2; c += dc) actions.push_back({'M', (dc > 0 ? 'R' : 'L')});
        for (int r = r1; r != r2; r += dr) actions.push_back({'M', (dr > 0 ? 'D' : 'U')});
    }
    cur_i = r2; cur_j = c2;
}

void apply_alter(int r, int c, char dir) {
    actions.push_back({'A', dir});
    int nr = r, nc = c;
    if (dir == 'U') nr--; if (dir == 'D') nr++; if (dir == 'L') nc--; if (dir == 'R') nc++;
    if(is_valid(nr,nc)) blocks[nr][nc] = !blocks[nr][nc];
}

void apply_slide(char dir) {
    actions.push_back({'S', dir});
    Point dest = get_slide_destination(cur_i, cur_j, dir, blocks);
    cur_i = dest.r; cur_j = dest.c;
}

double calculate_future_benefit(int k_idx, int br, int bc, const vector<vector<bool>>& current_blocks) {
    vector<vector<bool>> future_blocks = current_blocks;
    future_blocks[br][bc] = true;

    double total_benefit = 0;
    Point prev_pos = {targets[k_idx].first, targets[k_idx].second};

    for (int p_idx = k_idx + 1; p_idx < M; ++p_idx) {
        Point p_target = {targets[p_idx].first, targets[p_idx].second};
        int cost_moves = manhattan_distance(prev_pos.r, prev_pos.c, p_target.r, p_target.c);
        int min_total_cost = cost_moves;

        if (br == p_target.r + 1 && bc == p_target.c && prev_pos.r < p_target.r) {
            Point ss = {prev_pos.r, p_target.c};
            if (get_slide_destination(ss.r, ss.c, 'D', future_blocks).r == p_target.r)
                min_total_cost = min(min_total_cost, manhattan_distance(prev_pos.r, prev_pos.c, ss.r, ss.c) + 1);
        }
        if (br == p_target.r - 1 && bc == p_target.c && prev_pos.r > p_target.r) {
            Point ss = {prev_pos.r, p_target.c};
            if (get_slide_destination(ss.r, ss.c, 'U', future_blocks).r == p_target.r)
                min_total_cost = min(min_total_cost, manhattan_distance(prev_pos.r, prev_pos.c, ss.r, ss.c) + 1);
        }
        if (br == p_target.r && bc == p_target.c + 1 && prev_pos.c < p_target.c) {
            Point ss = {p_target.r, prev_pos.c};
            if (get_slide_destination(ss.r, ss.c, 'R', future_blocks).c == p_target.c)
                min_total_cost = min(min_total_cost, manhattan_distance(prev_pos.r, prev_pos.c, ss.r, ss.c) + 1);
        }
        if (br == p_target.r && bc == p_target.c - 1 && prev_pos.c > p_target.c) {
            Point ss = {p_target.r, prev_pos.c};
            if (get_slide_destination(ss.r, ss.c, 'L', future_blocks).c == p_target.c)
                min_total_cost = min(min_total_cost, manhattan_distance(prev_pos.r, prev_pos.c, ss.r, ss.c) + 1);
        }
        
        if (min_total_cost < cost_moves) {
            total_benefit += (cost_moves - min_total_cost);
        }
        prev_pos = p_target;
    }
    return total_benefit;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N >> M;
    int start_i, start_j;
    cin >> start_i >> start_j;
    targets.resize(M);
    targets[0] = {start_i, start_j};
    for (int i = 1; i < M; ++i) {
        cin >> targets[i].first >> targets[i].second;
    }

    blocks.assign(N, vector<bool>(N, false));
    cur_i = start_i;
    cur_j = start_j;

    for (int k = 1; k < M; ++k) {
        int ti = targets[k].first;
        int tj = targets[k].second;

        if (blocks[ti][tj]) {
            int best_ni = -1, best_nj = -1, min_dist = 1e9;
            int dr[] = {-1, 1, 0, 0}, dc[] = {0, 0, -1, 1};
            for (int i=0; i<4; ++i) {
                int ni = ti + dr[i], nj = tj + dc[i];
                if (is_valid(ni,nj) && !blocks[ni][nj] && manhattan_distance(cur_i,cur_j,ni,nj) < min_dist) {
                    min_dist = manhattan_distance(cur_i, cur_j, ni, nj);
                    best_ni = ni; best_nj = nj;
                }
            }
            apply_move(cur_i, cur_j, best_ni, best_nj, true);
            char adir = ' ';
            if (best_ni == ti-1) adir = 'D'; else if(best_ni == ti+1) adir = 'U';
            else if (best_nj == tj-1) adir = 'R'; else adir = 'L';
            apply_alter(cur_i, cur_j, adir);
            apply_move(cur_i, cur_j, ti, tj, true);
            continue;
        }

        double best_score = 1e9;
        int best_plan_type = -1; 
        bool best_v_first = true;
        Point best_block_to_place, best_slide_start;
        char best_slide_dir = ' ';

        int cost_moves = manhattan_distance(cur_i, cur_j, ti, tj);
        if (is_path_clear(cur_i, cur_j, ti, tj, true, blocks)) {
             best_score = cost_moves; best_plan_type = 0; best_v_first = true;
        }
        if (is_path_clear(cur_i, cur_j, ti, tj, false, blocks)) {
             if (cost_moves < best_score) {
                best_score = cost_moves; best_plan_type = 0; best_v_first = false;
             }
        }
        
        int dr[] = {-1, 1, 0, 0}, dc[] = {0, 0, -1, 1};
        char op_dir[] = {'D', 'U', 'R', 'L'};

        for (int i = 0; i < 4; ++i) {
            int br = ti + dr[i], bc = tj + dc[i];
            if (!is_valid(br, bc) || !blocks[br][bc]) continue;
            
            char slide_dir = op_dir[i];
            Point slide_start; int cost = -1; bool condition = false;
            
            if (slide_dir == 'D' && cur_i < ti) {
                slide_start = {cur_i, tj}; cost = manhattan_distance(cur_i, cur_j, cur_i, tj) + 1; condition = true;
            } else if (slide_dir == 'U' && cur_i > ti) {
                slide_start = {cur_i, tj}; cost = manhattan_distance(cur_i, cur_j, cur_i, tj) + 1; condition = true;
            } else if (slide_dir == 'R' && cur_j < tj) {
                slide_start = {ti, cur_j}; cost = manhattan_distance(cur_i, cur_j, ti, cur_j) + 1; condition = true;
            } else if (slide_dir == 'L' && cur_j > tj) {
                slide_start = {ti, cur_j}; cost = manhattan_distance(cur_i, cur_j, ti, cur_j) + 1; condition = true;
            }
            
            if(condition && cost < best_score) {
                 if (get_slide_destination(slide_start.r, slide_start.c, slide_dir, blocks).r == ti &&
                     get_slide_destination(slide_start.r, slide_start.c, slide_dir, blocks).c == tj &&
                     is_path_clear(cur_i, cur_j, slide_start.r, slide_start.c, true, blocks)) {
                    best_score = cost; best_plan_type = 1;
                    best_slide_start = slide_start; best_slide_dir = slide_dir;
                 }
            }
        }
        
        for (int i = 0; i < 4; ++i) {
            int br = ti + dr[i], bc = tj + dc[i];
            if (!is_valid(br, bc) || blocks[br][bc]) continue;
            
            int cost = manhattan_distance(cur_i, cur_j, ti, tj) + 1;
            double benefit = calculate_future_benefit(k, br, bc, blocks);
            double score = cost - ALPHA * benefit;

            if (score < best_score) {
                best_score = score; best_plan_type = 2; best_block_to_place = {br, bc};
            }
        }

        if (best_plan_type == 0) {
            apply_move(cur_i, cur_j, ti, tj, best_v_first);
        } else if (best_plan_type == 1) {
            apply_move(cur_i, cur_j, best_slide_start.r, best_slide_start.c, true);
            apply_slide(best_slide_dir);
        } else if (best_plan_type == 2) {
            apply_move(cur_i, cur_j, ti, tj, true);
            char adir = ' ';
            if (best_block_to_place.r == ti - 1) adir = 'U';
            else if (best_block_to_place.r == ti + 1) adir = 'D';
            else if (best_block_to_place.c == tj - 1) adir = 'L';
            else adir = 'R';
            apply_alter(cur_i, cur_j, adir);
        } else {
             apply_move(cur_i, cur_j, ti, tj, true);
        }
    }

    for (const auto& action : actions) {
        cout << action.first << " " << action.second << endl;
    }

    return 0;
}