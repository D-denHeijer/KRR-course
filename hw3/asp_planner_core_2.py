from planning import PlanningProblem, Action, Expr, expr
import planning

import re
import clingo

PLAN = None

def swap_case_first_letter(expression):
    return str(expression)[0].swapcase() + str(expression)[1:]


def parse_expression(expression):
    operator = swap_case_first_letter(expression.op)

    arguments = []
    for arg in expression.args:
        arguments += [swap_case_first_letter(arg)]

    if arguments == []:
        return operator
    else:
        return operator + "({})".format(','.join(arguments))


def initialise_plan(planning_problem, t_max):
    time_steps = "time(0..{}).\n".format(t_max-1)

    initial_state = ""
    for exp in planning_problem.initial:
        initial_state += "state(0,{}).\n".format(parse_expression(exp))

    return time_steps + initial_state


def parse_action(action):
    words = re.findall(r'\w+', str(action))

    operator = swap_case_first_letter(words[0])

    arguments = []
    for word in words[1:]:
        arguments += [swap_case_first_letter(word)]

    if arguments == []:
        return operator
    else:
        return operator + "({})".format(','.join(arguments))


def encode_actions(planning_problem):
    action_rules = ""
    for action in planning_problem.actions:
        available_rule = "available(T,{}) :- not goal(T), time(T)".format(parse_action(action))
        if action.precond == []:
            available_rule = "available(T,{}) :- time(T), not goal(T)".format(parse_action(action))
        else:
            for precond in action.precond:
                # prevents unsafe variable...
                if str(precond)[0] == '~':
                    precond = expr(str(precond)[1:])
                    available_rule += ", not state(T,{})".format(parse_expression(precond))
                else:
                    available_rule += ", state(T,{})".format(parse_expression(precond))

        fluent_rule = "state(T,S) :- time(T), state(T-1,S), chosen(T-1,{})".format(parse_action(action))
        effect_rule = ""
        for effect in action.effect:
            if str(effect)[0] == '~':
                fluent_rule += ", S!={}".format(parse_action(effect))
            else:
                effect_rule += "state(T,{}) :- time(T), chosen(T-1,{}).\n".format(parse_action(effect),parse_action(action))

        action_rules += effect_rule + (fluent_rule+".\n") + (available_rule+".\n")

    return action_rules


def encode_goals(planning_problem):
    goals = []
    for goal in planning_problem.goals:
        if str(goal)[0] == '~':
            goal = expr(str(goal)[1:])
            goals += ["not state(T,{})".format(parse_expression(goal))]
        else:
            goals += ["state(T,{})".format(parse_expression(goal))]

    goal_rule = "goal(T) :- " + "{}.\n".format(', '.join(goals))
    integrity_constraint = ":- time(T), not goal(_).\n"
    optimization_rule = "#minimize{T : goal(T)}.\n"

    return goal_rule + integrity_constraint + optimization_rule


def get_plan(sorted_model):
    plan = []
    for chosen in sorted_model:
        words = re.findall(r'\w+', chosen)
        operator = swap_case_first_letter(words[2])
        arguments = [swap_case_first_letter(arg) for arg in words[3:]]
        plan += [operator + "({})".format(', '.join(arguments))]

    return plan


def on_model(model):
    if model.optimality_proven == True:
        sorted_model = [str(atom) for atom in model.symbols(shown=True)]
        sorted_model.sort()
        global PLAN
        PLAN = get_plan(sorted_model)


def solve_planning_problem_using_ASP(planning_problem,t_max):
    """
    If there is a plan of length at most t_max that achieves the goals of a given planning problem,
    starting from the initial state in the planning problem, returns such a plan of minimal length.
    If no such plan exists of length at most t_max, returns None.

    Finding a shortest plan is done by encoding the problem into ASP, calling clingo to find an
    optimized answer set of the constructed logic program, and extracting a shortest plan from this
    optimized answer set.

    NOTE: still needs to be implemented. Currently returns None for every input.

    Parameters:
        planning_problem (PlanningProblem): Planning problem for which a shortest plan is to be found.
        t_max (int): The upper bound on the length of plans to consider.

    Returns:
        (list(Expr)): A list of expressions (each of which specifies a ground action) that composes
        a shortest plan for planning_problem (if some plan of length at most t_max exists),
        and None otherwise.
    """

    asp_code = initialise_plan(planning_problem, t_max)
    asp_code += encode_actions(planning_problem)
    asp_code += "{chosen(T,A) : available(T,A)}=1 :- time(T), available(T,_).\n"
    asp_code += encode_goals(planning_problem)

    asp_code += "#show chosen/2."
    print(asp_code)

    control = clingo.Control()
    control.add("base", [], asp_code)
    control.ground([("base", [])])

    control.configuration.solve.opt_mode = "optN"
    control.configuration.solve.models = 1

    answer = control.solve(on_model=on_model)

    return PLAN
